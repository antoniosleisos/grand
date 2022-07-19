#! /usr/bin/env python3

'''
Created on 19 juil. 2022

@author: Jean-Marc Colley, CNRS/IN2P3/LPNHE

'''
import tarfile
import os
import sys
import os.path as osp
from urllib import request
#TODO: add progressbar to grand lib
#import progressbar

from grand import GRAND_DATA_PATH, grand_add_path_data

LINK_MODEL = "https://forge.in2p3.fr/attachments/download/133380/grand_model_2207.tar.gz"
FILE_MODEL = "grand_model_2207.tar.gz"



# class MyProgressBar():
#     def __init__(self):
#         self.pbar = None
#
#     def __call__(self, block_num, block_size, total_size):
#         if not self.pbar:
#             self.pbar=progressbar.ProgressBar(maxval=total_size)
#             self.pbar.start()
#
#         downloaded = block_num * block_size
#         if downloaded < total_size:
#             self.pbar.update(downloaded)
#         else:
#             self.pbar.finish()



# 1- test if download is necessary
if os.path.exists(grand_add_path_data('detector')):
    print('Skip download')
    sys.exit(0)

tar_file = osp.join(GRAND_DATA_PATH, FILE_MODEL)

# 2- download
print("Download data model for GRAND")
try:
    request.urlretrieve(LINK_MODEL, tar_file)
    print("Successfully downloaded")
except:
    print(f"download failed {LINK_MODEL}")
    sys.exit(1)
    
# 3- extract
print('Extract tar file')
try:
    my_tar = tarfile.open(tar_file)
    my_tar.extractall(GRAND_DATA_PATH) 
    my_tar.close()
except:
    print(f"Extract failed '{tar_file}'")
    sys.exit(1)
sys.exit(0) 
