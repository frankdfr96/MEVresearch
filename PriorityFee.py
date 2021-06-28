 
import math
import numpy as np
from numpy.random import *
import matplotlib.pyplot as plt
import matplotlib
import urllib.request as urlreq
import json
from math import *
from functools import reduce
import warnings
import csv



class PriorityArea:
    
    def __init__(self, lastBlockNumber="", daysBack=30):
        self.lastBlockNumber=lastBlockNumber
        self.daysBack = daysBack
        self.blocks = self.load_blocks(self.lastBlockNumber, self.daysBack)
        self.rewards = np.array([int(block["miner_reward"])*weiToEth for block in self.blocks])
        self.original_gas = np.array([gas_used(block) for block in self.blocks])
        self.n_blocks = len(self.blocks)
        self.daily_gas_prices = self.load_daily_gas_prices()


    #lastBlockNumber="" corresponds to latest="" in the flashbots API, downloading from the last available block
    def load_blocks(self, lastBlockNumber, daysBack):
            try: 
                #Load Blocks from file
                f = open("blocksFrom{}To{}DaysBack.txt".format(lastBlockNumber, daysBack), "r")
                blocks = json.loads(f.read())
            except: 
                #Download blocks from Flashbots API
                headers = {'User-Agent': 
                        'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:76.0) Gecko/20100101 Firefox/76.0'}
                load_size = 10000
                daysPerLoad = load_size*13/(24*3600)
                latest = lastBlockNumber
                blocks = []
                for _ in range(int(daysBack/daysPerLoad)):
                    url = 'https://blocks.flashbots.net/v1/blocks?limit={}&before={}'.format(load_size, latest)
                    req = urlreq.Request(url=url, headers=headers)
                    data = urlreq.urlopen(req).read()
                    dic = json.loads(data)
                    blocks += dic["blocks"]
                    latest = blocks[-1]["block_number"]


                f = open("blocksFrom{}To{}DaysBack.txt".format(blocks[0]["block_number"], daysBack), "w+")
                f.write(json.dumps(blocks))
            finally:
                f.close()
                blocks = [block for block in blocks if int(block["miner_reward"]) > 0]
                blocks = blocks[::-1] #First block is the oldest one
                return blocks
            
    def load_daily_gas_prices(self):
        daily_gas_prices = []
        with open('export-AvgGasPrice.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=',')
            for row in reader:
                date = row["Date(UTC)"].split("/")
                if int(date[2]) == 2021:
                    if (int(date[0]) == 4 and int(date[1]) >= 22) or int(date[0]) == 5 or (int(date[0]) == 6 and int(date[1]) <= 24):
                        daily_gas_prices.append(int(row["Value (Wei)"])*weiToGwei)
        return daily_gas_prices
                        
    def block_to_price(self, block):
        n_days = len(self.daily_gas_prices)
        blocks_interval = (int(self.blocks[-1]["block_number"]) - int(self.blocks[0]["block_number"]))
        return self.daily_gas_prices[int((n_days-1)*(int(block["block_number"]) - int(self.blocks[0]["block_number"]))/blocks_interval)]

        
    # GAS BASED PRICING, WITH PRIORITY GAS TARGET

    # doubling_blocks: how many blocks it takes for the priority fee to double at 2*target gas consumption
    def gas_based(self, blocks, target=200000, init_fee=100, time_to_double=6):
        n_blocks = self.n_blocks
        #new_rewards = np.zeros(n_blocks)
        priority_fee = init_fee
        fee = np.zeros(n_blocks)
        priority_gas = np.zeros(n_blocks)
        burnt = np.zeros(n_blocks)
        increase_factor = 2**(1/time_to_double) - 1
        #time_to_half = 9
        #decrease_factor = np.exp((log(0.5)/time_to_half))
        for i, block in enumerate(self.blocks):
            for tx in block["transactions"]:
                if  priority_fee*gweiToEth < int(tx["gas_price"])*weiToEth:
                    tx_gas = int(tx["gas_used"])
                    tx_burn = tx_gas*priority_fee*gweiToEth
                    tx_payment = int(tx["total_miner_reward"])*weiToEth
                    priority_gas[i] += tx_gas
                    burnt[i] += tx_burn
            priority_fee *= 1 + increase_factor*(priority_gas[i] - target)/target
            fee[i] = priority_fee
        
        return fee, burnt, priority_gas

    # ONE-OFF FEE PRICING

    def one_off(self, blocks, init_fee=0.1, time_to_double=6, time_to_half=7):
        n_blocks = self.n_blocks
        priority_fee = init_fee
        new_rewards = np.zeros(n_blocks)
        fee = np.zeros(n_blocks)
        priority_gas = np.zeros(n_blocks)
        burnt = np.zeros(n_blocks)
        increase_factor = 2**(1/time_to_double)
        decrease_factor = 0.5**(1/time_to_half)

        for i, block in enumerate(self.blocks):
            new_rewards[i] = max(self.rewards[i] - priority_fee,0)
            if new_rewards[i] > 0:
                burnt[i] = priority_fee
                priority_fee *= increase_factor
                priority_gas[i] = gas_used(block)
            else:
                priority_fee *= decrease_factor
            fee[i] = priority_fee
        return fee, burnt, priority_gas


    # HYBRID PRICING
        
    def hybrid(self, blocks, init_one_off_fee=0.1, init_gas_fee=50, target=200000,
            time_to_double=6, time_to_half=7, gas_doubling_blocks=6, fixed_gas_fee=False, bribes_percentage = 90):
        n_blocks = self.n_blocks
        viable_gas = np.zeros(n_blocks)
        one_off_fee = np.zeros(n_blocks)
        gas_fee = np.ones(n_blocks)*init_gas_fee #gwei
        one_off_fee[0] = init_one_off_fee # ETH
        priority_gas = np.zeros(n_blocks)
        burnt = np.zeros(n_blocks)
        increase_factor = 2**(1/time_to_double)
        decrease_factor = 0.5**(1/time_to_half)
        gas_increase_factor = np.exp((log(2)/gas_doubling_blocks)) - 1
        new_rewards = 0
        
        for i, block in enumerate(self.blocks):
            gas_fee[i] = max(gas_fee[i], self.block_to_price(block)) #SET THE PRIORITY GAS FEE TO BE AT LEAST THE AVG DAILY GAS FEE
            for tx in block["transactions"]:
                tx_gas = int(tx["gas_used"])
                tx_burn = tx_gas*gas_fee[i]*gweiToEth
                tx_payment = (100/bribes_percentage)*int(tx["total_miner_reward"])*weiToEth
                if  tx_burn <= tx_payment:
                    #tx can profitably be included
                    new_rewards += tx_payment - tx_burn
                    priority_gas[i] += tx_gas
                    burnt[i] += tx_burn
                viable_gas[i] = priority_gas[i]
            if new_rewards > one_off_fee[i] - burnt[i]:
                burnt[i] = max(burnt[i], one_off_fee[i])
                if i+1 < n_blocks: one_off_fee[i+1] = one_off_fee[i]*increase_factor
            else:
                burnt[i] = 0
                priority_gas[i] = 0
                if i+1 < n_blocks: one_off_fee[i+1] = one_off_fee[i]*decrease_factor
            if i+1 < n_blocks and not fixed_gas_fee: gas_fee[i+1] = gas_fee[i]*(1 + gas_increase_factor*(priority_gas[i] - target)/target)
            new_rewards = 0
                
        return one_off_fee, gas_fee, burnt, priority_gas, viable_gas
            


    def print_results(self, burnt, priority_gas, gas_fee=None, one_off_fee = None, text=True, plot=True, title="Results", verbose=False):
        print(title)
        percentile = np.percentile(self.rewards, 90)
        non_outliers = [i for i, r in enumerate(self.rewards) if r < percentile]
        if text:
            if gas_fee is not None:
                print("Median priority gas price: {:.0f} gwei".format(np.median(gas_fee)))
                print("Mean priority gas price: {:.0f} gwei".format(np.mean(gas_fee)))
            if one_off_fee is not None:
                print("Median one-off fee: {:.3f} eth".format(np.median(one_off_fee)))
                print("Mean one-off fee: {:.3f} eth".format(np.mean(one_off_fee)))
            print("Mean burn: {:.3f} eth".format(np.mean(burnt)))
            print("Average burn percentage: {:.1f}%".format(100*np.mean(burnt/self.rewards)))
            print("Total burn percentage: {:.1f}%".format(100*np.sum(burnt)/np.sum(self.rewards)))
            print("Mean priority gas utilization: {:.1f}%".format(100*np.mean(priority_gas/self.original_gas)))
            print("Percentage of missed slots: {:.1f}%".format(100*np.mean(burnt == 0)))
            if verbose:
                print("Median gas used: {:.0f}".format(np.median(self.original_gas)))
                print("Median priority gas: {:.0f}".format(np.median(priority_gas)))
                print("Mean gas used: {:.0f}".format(np.mean(self.original_gas)))
                print("Mean priority gas: {:.0f}".format(np.mean(priority_gas)))
                print("Average burn percentage without outliers: {:.1f}%".format(100*np.mean(burnt[non_outliers]/self.rewards[non_outliers])))
                print("Total burn percentage without outliers: {:.1f}%".format(100*np.sum(burnt[non_outliers])/np.sum(rewards[non_outliers])))
                print("Percentage of outliers: {:.1f}%".format(100*(n_blocks - len(non_outliers))/self.n_blocks))
        if plot:
            if gas_fee is not None:
                plt.plot(gas_fee, color = 'r')
                plt.title("Priority gas fee (gwei)")
            if one_off_fee is not None:
                plt.figure()
                plt.plot(one_off_fee, color = 'r')
                plt.title("One-off fee (eth)")
            plt.figure()
            plt.plot(self.rewards, color = 'b')
            plt.plot(burnt, color = 'r')
            plt.legend(["rewards", "burnt"])
            plt.title("original rewards and burnt component")
            plt.figure()
            plt.title("original rewards and burnt component, no outliers")
            plt.plot(self.rewards[non_outliers], color = 'b')
            plt.plot(burnt[non_outliers], color = 'r')
            plt.legend(["rewards", "burnt"])
            plt.figure()
            plt.plot(self.original_gas)
            plt.plot(priority_gas)
            plt.legend(["Gas used", "Priority gas"])
            plt.show()
        print("\n\n")