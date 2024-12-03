python /workspace/AI-avatar-headshot/Dreambooth_SDXL/train_dreambooth_lora_sdxl.py \
 --pretrained_model_name_or_path="SG161222/RealVisXL_V5.0" \
 --instance_data_dir="/workspace/AI-avatar-headshot/Data/Veronika" \
 --class_data_dir="/workspace/AI-avatar-headshot/Data/Veronika_class" \
 --instance_prompt='a portrait photo of veronika01' \
 --class_prompt='a portrait photo of woman, realistic, detailed,(high detailed skin:1.2), 8k uhd, dslr, soft lighting, high quality, film grain'\
 --with_prior_preservation \
 --num_class_images=50 \
 --output_dir="/workspace/AI-avatar-headshot/Dreambooth_SDXL/model_checkpoint_Veronika" \
 --seed=62 \
 --resolution=768 \
 --center_crop \
 --train_text_encoder \
 --train_batch_size=4 \
 --num_train_epochs=10 \
 --max_train_steps=1501 \
 --checkpointing_steps=20000 \
 --gradient_accumulation_steps=1\
 --gradient_checkpointing \
 --learning_rate=2e-6 \
 --use_8bit_adam \
 --report_to='wandb' \
 --mixed_precision='bf16' \
 --rank=48
