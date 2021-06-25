# In-protocol separation of priority-sensitive and insensitive transactions as an MEV mitigation strategy (and more)


As it is known, there's two very different kinds of transactions in Ethereum blocks: ones that care about the order and ones that do not, or at least not strongly enough to compete for it. The most common kind of transaction of the first type cares specifically about priority, because it obtains its value by being first to some MEV extraction opportunity, and is willing to pay much higher fees to be first among the relevant competing transactions.

We define the value extractable by such transactions as Priority MEV, from now on called pMEV. One example of this is "previous block state MEV", which is all MEV that depends only on the state of the previous block, and will thus be extracted by the first relevant tx in the new block. Arbitrage and liquidations that do not depend on backrunning mempool txs are instances of this. Another one are Compound liquidations, which can be executed by anyone that includes a signed oracle update. Some backrunning MEV can be converted into pMEV with the right design, as the latter example shows. In fact, this is also one of the effects of Flashbots bundles: instead of trying to backrun an oracle update or a large swap through spam, these txs can be included in a bundle and backrun there. The competition is therefore shifted to getting at the front of the block, which in this case means providing the most valuable bundle. 

The value from such transactions is currently almost entirely harvested by miners, because the protocol has no control over ordering nor makes any restrictions about it, and thus it can only indiscriminately charge for blockspace. Moreover, variability in MEV and in miners' (and later proposers') ability to extract it create risks of centralization and consensus instability.

We propose explicitly separating priority-sensitive and insensitive transactions in-protocol, enabling the value of the former to be recaptured and redistributed in a way that mitigates such risks, either through burning or sharing of profits among validators. While the proposal is written thinking about Ethereum L1, it could just as well apply to some L2



## Priority Transactions


Transactions, or whole bundles, could be marked as priority transactions, ptxs, distinguished from rtxs, regular transactions. Ptxs can only be executed in the first position of a block which is at a specified height and built on top of a specified head of the chain. Possibly something like Flashbots' bundle merging could be implemented, and independent bundles could all be executed as ptxs, in arbitrary order (since they are independent) but before all  rtxs. 

To prevent block proposers from ignoring ptxs, control over the ordering of the rtxs would have to be taken away from them, through randomization and delayed execution. One can think of it as the block being split into a priority area, P, whose transactions are executed all at the same time, and a regular (or randomized) area, R, whose order is determined later so it cannot be manipulated by the proposer 

Ptxs can be priced differently from rtxs, which can be used to reduce the risks associated with MEV, for example through burning or socializing profits


## Advantages


- **Reduction of MEV-driven risk to consensus:** if successful at capturing a substantial portion of the "basal level" pMEV, it would help to mitigate the potential of consensus instability and centralization caused by what's perhaps the largest, most consistent component of MEV. Quite simply, both burning and socializing profits among validators reduce the effective amount of MEV that can be stolen by destabilizing consensus or which can give a higher earning potential to powerful proposers.
- **Harm-minimizing way of taking ordering away from proposers:**  having a ptx (or bundle) which executes most pMEV might allow randomization of transaction ordering without some of the negative effects. In particular, it gives an avenue for pMEV to happen without having to compete via spamming, which is what would happen in a fully randomized block. The remaining issue is other potential spam sources, some of which are maybe addressed in the following bullet point. 

    The assumption here is that randomized ordering of transactions is an improvement if it can be implemented without hindering positive MEV or creating spam. The idea is that ordering power is a source of MEV by itself, and often of the kind of MEV that directly harms users, like sandwiching. For example, if the latter can be performed risk-free by a proposer (or by a searcher, as through Flashbots), the [Minimum Victim Input](https://arxiv.org/pdf/2009.14021.pdf) to be profitable in expectation decreases, and more txs become sandwichable. By randomizing, there is no participant that can sandwich risk-free, not even proposers. 
    
    Moreover, the cost is necessarily higher: if you want to frontrun in this new kind of block, you either pay the higher priority fee or have to do statistical frontrunning by sending a few txs (which is costly even for proposers after EIP 1559). Both result in higher costs than what is possible now: even post EIP 1559, a proposer/flashbots searcher does not need to pay the basefee for any failed txs. The backrunning part of sandwiching can only be done statistically, also subject to strictly higher costs than currently.
    
    Finally, randomization makes it so the risks of sandwiching increase with the number of $txs/block$ that a pool gets. The higher the number of txs to the pool in a block, the more expensive it becomes to target a specific one. This acts against the fact that users need to set higher slippage when interacting with pools that are receiving many txs. When this is not the case, setting a low slippage already serves as protection.
    
    


- **Backrunning spam mitigation (with benefits):** to further mitigate spam, both preexisting and arising as a consequence of the randomization, a tx could be marked by its issuer as "bundlable", meaning it can be inserted into a priority bundle. If it is inserted, the issuer of the tx receives some payment from that of the priority bundle. Maybe the latter simply pays for gas, or the former is able to express what payment they require, which they could do based on their evaluation of the MEV that the tx exposes. Such a tx could also be normally inserted in R, and in that case it behaves like every rtx. 
    
    Oracle txs, low slippage swaps, or any txs that are not at risk of being frontrun but can be profitably backrun, could be marked this way, so they can be backrun in the priority bundle. Effectively, this converts some MEV to pMEV. Moreover, the value they expose is partially returned to the issuers, and there's less incentives for spam. The gain for oracles might be particularly meaningful, since they especially suffer from high tx fees due to the very high time preference. Moreover, the fees are highest when the updates are needed the most, but on the other end that's also when backrunning them can be most valuable


## Relationship with Flashbots:

Blocks containing Flashbots bundles essentially operate like the blocks in scenario 3, except for the fact that a tx cannot opt-out of being included in a Flashbots bundle, which enables safe exploitation of any tx in them (like sandwiching). Priority bundles would either be only composed of actual priority txs or also of other txs that opt-in and are able to require a payment for it. Even if Flashbots wanted to implement a similar scheme, there is no reason for proposers to go along with it unless it is part of the validity conditions of a block.

Something that Flashbots offers that this scheme could not offer is a private relay channel for searchers, offering pre-trade privacy and failed trade privacy. The former is especially important since the lack thereof is a centralization vector, potentially leading searchers to make deals with large proposers they can trust, which makes the earning potential of the latter greater than that of the ones that are excluded. Nonetheless, a private relay channel, as the whole Flashbots infrastracture, can work with this scheme.


## Pricing 

These are some of the possible schemes, involving what exactly is priced and how the price is dynamically adjusted.

1. **Gas-based fee**: Ptxs pay a gas price higher than the basefee (though no more than the basefee needs to be burnt). The price can be adjusted in different ways, for example simply as a multiple of the basefee. Alternatiely, P and R can have their own separate EIP-1559 fee mechanism, with separate gas targets. P does not need necessarily need to have a hard gas limit, and probably shouldn't. The target is necessary for pricing, but otherwise you would want as many ptxs as possible to be in P rather than being converted to spam in R.
2. **One-off fee:** The block proposer has to pay a one-off fee for the block to have a priority area at all. Transactions just pay the basefee and otherwise compensate the proposer however they wish. An empty priority area decreases the fee, otherwise it increases. How much "priority gas" is consumed is irrelevant for the price. A priority gas limit is needed.
3. **Hybrid:** A one-off fee is required for there to be a priority area at all, but each ptx is also charged a higher fee for gas.


There are tradeoffs involved, which I am trying to explore by using data from the [Flashbots API](https://blocks.flashbots.net/). This is an ongoing effort, which you can take a look at here: [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/frankdfr96/MEVresearch/HEAD)


## Issues:

### Risk of OCA (Off-Chain Agreement) to avoid randomization:

This particular OCA is possible in general, but it is especially easy in a post-EIP3074 world. An Invoker contract is setup by a miner/validator cartel, and when the priority fee becomes too high with respect to the available pMEV, participating users and searchers are required to submit auth-messages and tx data off-chain, which are all are bundled in one tx to the Invoker, leaving the cartel in control of the order without paying the required fee.

This does not even require the users/searchers to setup a special smart contract wallet which does the signature verification (which would be the case without 3074), since the authcall executes the calls with the desired sender. It is also not too complicated from an organizational standpoint, since sending EIP3074 transactions might become commonplace and easy to do.

The main hurdle becomes at this point the fact that normal users won't have any reason to go through the extra steps to submit txs this way, except for the risk of being censored. On the contrary, many will have an incentive not to do so, because they would allow themselves to be exploited.
Block proposers don't gain much from including regular txs post EIP1559, but repeated exclusion would make tips rise, and thus sustaining the OCA more costly. Moreover, the obvious situations in which there might a lot to gain from avoiding the priority fee are a flash crash, a period of high volatility, a token launch etc... In these, there might be a sustained level of high pMEV, at least for long enough for the priority fee to catch up and create a compelling incentive to avoid it. On the other end, in these situations blocks might also be often full and tips higher than normal, also making the OCA more expensive.


### Priority transactions being forced into the regular area

When considering what the optimal priority fee might be for a single block, there's a complex relationship (not exactly a tradeoff) between maximizing collected fees (and thus MEV mitigation) and allowing as many priority transactions as possible in P. The latter is desirable so that they don't get converted into spam in R and so that positive pMEV can always be executed when needed. 

If pricing is gas-based, a higher fee enables more value to be recovered from the highest value ptxs, which can be significantly more valuable than other ptxs, with a power-law-like distribution, and thus overall lead to more burning or redistribution. On the other end, less ptxs are allowed in P.

If the pricing is through a one-off fee, a higher fee does not necessarily price out low-value ptxs, because any profitable one is worth including if the one-off fee can be at all paid. Nonetheless, capturing a substantial portion of pMEV requires "aggressive" price adjustements which can cause the one-off fee to at times be too onerous, pricing out all ptxs at once. Moreover, we are forced to introduce a hard priority gas limit.


##### Bundle Merging
To mitigate this issue, we'd like to be able to include multiple priority bundles, as Flashbots currently does. This leads to some issues, reminiscent of some of the ones mentioned in [MEV-SGX: A sealed bid MEV auction design](https://ethresear.ch/t/mev-sgx-a-sealed-bid-mev-auction-design/9677). In particular, we have three obvious options, all with flaws:


- The simplest option is to allow dependent ptxs and require a payment regardless of how they execute. Proposers would then be incentivized to include all ptxs, including all failed ones, which is bad for searchers and needlessly fills up the block, negating the positive effects of moving the MEV competition off-chain. 
- The proposer pays for the fee and is paid directly by the ptxs if they execute successfully (as with Flashbots). This does not require an additional block validity criterion about state independence, because the proposer is the only one that has something to lose from including failed ptxs. The problem with this is that the proposer has to execute potentially computationally intensive txs without being sure about the payment, so it introduces a DoS risk. 
- There could be a validity criterion requiring the txs to be independent, and all payments could then be upfront, meaning the proposer would just check that the sender has a sufficient balance to pay the specified fee. This does not put senders in jeopardy of paying a fee without earning enough from the tx, because they know exactly how their ptx will execute. In fact, independence means any state in which their ptx could execute is equivalent to the state of the last block, as far as they're concerned. The problem with this is that it doesn't solve the issue from before: payment is only guaranteed after independence is verified, and checking for independence requires running the txs


A partial solution might be to require ptxs to somehow list what state they interact with. It would be required for propagation but not posted on chain unless it is incorrect, in which case it can be posted as a fraud proof, to penalize lying senders. This way it normally does not take up space on chain. 

This still leaves open the possibility of spamming the network with conflicting txs for free, since at most one will execute. It could be mitigated through further propagation rules, but there's no obvious way to choose them, since there's a priori nothing wrong with propagating two conflicting txs and leaving the choice to the proposer



### Properties of the randomization

Ideally, randomization would happen in a way that is not manipulable by the current proposer (even if they are the proposer for the next block as well) and whose results are available before the next block is posted, so that there's a period of time in which the state is known and can be interacted with deterministically. This is especially important for ptxs themselves, and failing to provide this could harm positive pMEV by making it less efficient.

To my knowledge, the current design of randomness in ETH2 does not satisfy these properties. Would they be feasible to satisfy with a different design, perhaps in an L2? Is this the case for any of coming ones?
