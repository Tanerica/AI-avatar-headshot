from train import train as train_pti
import os
import sys
sys.path.append("pti_trainer")
# os.environ['DISABLE_AUTO_CAPTIONS'] = 'false' 
TRAINING_MODEL_DIR = "/workspace/output_cog"
train_pti(
    input_images=f"/workspace/training_sdxl_pti/tan25/",
    output_dir=TRAINING_MODEL_DIR,
    pretrained_model_name_or_path="stabilityai/stable-diffusion-xl-base-1.0",
    seed= 62,
    resolution=768,
    train_batch_size= 4,
    num_train_epochs= 4000,
    max_train_steps=3000,
    is_lora=True,
    is_sdxl=True,
    unet_learning_rate= 3e-6,
    ti_lr= 3e-4,
    lora_lr= 1e-4,
    lora_rank=32,
    class_name="man",
    token_string="ta2kn",
    caption_prefix= 'a photo of',
    checkpointing_steps=1000,
    # Uses CLIPSEG to mask target in the loss function
    # mask_target_prompts=tune.name if use_photo and (tune.mask_target or os.environ.get('MASK_TARGET')) else None,
    mask_target_prompts = None
    # *(['--use_face_detection_instead', 'USE_FACE_DETECTION_INSTEAD'] if tune.face_crop and tune.name in "man woman boy girl male female" else []),
)
