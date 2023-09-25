# Netket_excited_state

## code 
The code written is based on existing Netket implementation of ground state variational Monte Carlo algorithm 

`vmc_ex.py`: The penalty excited state version of the vmc driver for ground state in Netket. 

`expect_grad_ex`: The penalty excited state version of the helper function called in vmc_ex.py driver.

`excited_state_demo.ipynb`: A demo of obtaining the second excited state given approximate ground state and first excited state. The notebook also shows a plot of how the state energy converges to the correct energy level.  

`Data`: This folder contains the previously obtained approximate ground state and first excited state in neural network quantum state form (variational parameters). The energy descent data will also be stored here.

## reference
The quantum many-body problem studied in this demo can be found in [this paper] (https://arxiv.org/abs/2307.03310)
