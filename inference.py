import argparse
import os
import random
import time

import numpy as np
import torch
import torch.backends.cudnn as cudnn
import gradio as gr

import esm
from minigpt4.common.config import Config
from minigpt4.common.dist_utils import get_rank
from minigpt4.common.registry import registry
from minigpt4.conversation.conversation_esm import Chat, CONV_VISION

import json

# Imports PIL module
from PIL import Image

# imports modules for registration
from minigpt4.datasets.builders import *
from minigpt4.models import *
from minigpt4.processors import *
from minigpt4.runners import *
from minigpt4.tasks import *

import esm
import esm.inverse_folding

def parse_args():
    parser = argparse.ArgumentParser(description="Demo")
    parser.add_argument("--cfg-path", required=True, help="path to configuration file.")
    parser.add_argument("--gpu-id", type=int, default=0, help="specify the gpu to load the model.")
    # parser.add_argument("--json-path", default='/home/h5guo/shared/Mini-GPT4/coco_json/cocoval2014_img_prompt.json', help="path to the classification json file")
    # parser.add_argument("--caption-save-path", default='/home/h5guo/shared/Mini-GPT4/coco_json_result/results.json', help="path to saved generated captions")
    parser.add_argument(
        "--options",
        nargs="+",
        help="override some settings in the used config, the key-value pair "
        "in xxx=yyy format will be merged into config file (deprecate), "
        "change to --cfg-options instead.",
    )
    args = parser.parse_args()
    return args


def setup_seeds(config):
    seed = config.run_cfg.seed + get_rank()

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)

    cudnn.benchmark = False
    cudnn.deterministic = True


# ========================================
#             Model Initialization
# ========================================

print('Initializing Chat')
args = parse_args()
cfg = Config(args)

model_config = cfg.model_cfg
model_config.device_8bit = args.gpu_id
model_cls = registry.get_model_class(model_config.arch)
model = model_cls.from_config(model_config).to('cuda:{}'.format(args.gpu_id))

vis_processor_cfg = cfg.datasets_cfg.cc_sbu_align.vis_processor.train
vis_processor = registry.get_processor_class(vis_processor_cfg.name).from_config(vis_processor_cfg)
chat = Chat(model, vis_processor, device='cuda:{}'.format(args.gpu_id))
print('Initialization Finished')

# ========================================
#             Gradio Setting
# ========================================

def gradio_reset(chat_state, img_list):
    if chat_state is not None:
        chat_state.messages = []
    if img_list is not None:
        img_list = []
    return chat_state, img_list

def upload_protein(gr_img):
    chat_state = CONV_VISION.copy()
    img_list = []
    llm_message = chat.upload_protein(gr_img, chat_state, img_list)
    return chat_state, img_list

def gradio_ask(user_message, chat_state):
    chat.ask(user_message, chat_state)
    return chat_state


def gradio_answer(chat_state, img_list, num_beams=1, temperature=1e-3):
    llm_message = chat.answer(conv=chat_state,
                              img_list=img_list,
                              num_beams=num_beams,
                              temperature=temperature,
                              max_new_tokens=300,
                              max_length=2000)[0]
    return llm_message, chat_state, img_list

if  __name__ == "__main__":
    start = time.time()
    print("******************")
    protein_embedding_path = "/home/h5guo/data/esm_subset/pt/2wge.pt"
    protein_embedding = torch.load(protein_embedding_path, map_location=torch.device('cpu'))
    sample_protein = protein_embedding.to('cuda:{}'.format(args.gpu_id))

    user_message = "Describe this protein in a short paragraph."
    chat_state, img_list = upload_protein(sample_protein)
    chat_state = gradio_ask(user_message, chat_state)
    llm_message, chat_state, img_list = gradio_answer(chat_state, img_list)

    print(f"llm_message: {llm_message}")
    end = time.time()
    print(end - start)
    # i += 1
    print("******************")
    # f.close()



