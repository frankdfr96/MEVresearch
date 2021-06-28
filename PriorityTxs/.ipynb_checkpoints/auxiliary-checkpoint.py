import math
import numpy as np
import matplotlib.pyplot as plt
from functools import reduce
import warnings
import csv


warnings.filterwarnings("ignore", 'Creating legend with loc="best" can be slow with large amounts of data.')
#Setup
resize = 0.8
plt.rcParams['figure.figsize'] = [resize*25/2.54, resize*20/2.54]
weiToEth = 10**-18
EthToGwei = 10**9
gweiToEth = 10**(-9)
weiToGwei = 10**(-9)
GweiToWei = 10**9
gas_used = lambda block: int(block["gas_used"])
gas_price = lambda block: int(block["gas_price"])*weiToEth
miner_reward = lambda block: int(block["miner_reward"])*weiToEth


def get_local_maxs(l, within=100):
    def red_fun(a,b):
        if a == []:
            return [b]
        i = a[-1][0]
        r1 = a[-1][1]
        j = b[0]
        r2 = b[1]
        if j - i > within:
            a += [(j, r2)]
        elif r2 > r1:
            a[-1] = (j,r2)
        return a

    return reduce(red_fun, enumerate(l), [])