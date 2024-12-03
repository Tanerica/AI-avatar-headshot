python /workspace/AI-avatar-headshot/Dreambooth_SD_1.5/train_dreambooth.py \
 --pretrained_model_name_or_path="SG161222/Realistic_Vision_V2.0" \
 --instance_data_dir="/workspace/AI-avatar-headshot/Data/Ali_sd15" \
 --class_data_dir="/workspace/AI-avatar-headshot/Data/Ali_sd15_class" \
 --instance_prompt='a portrait of [ali01] man, realistic, detailed,(high detailed skin:1.2), 8k uhd, dslr, soft lighting, high quality' \
 --class_prompt='a portrait of a young man, short hair, realistic, detailed,(high detailed skin:1.2), 8k uhd, dslr, soft lighting, high quality, film grain, Fujifilm XT3'\
 --with_prior_preservation \
 --num_class_images=40 \
 --output_dir="/workspace/AI-avatar-headshot/Dreambooth_SD_1.5/model_checkpoint" \
 --seed=62 \
 --resolution=768 \
 --center_crop \
 --train_text_encoder \
 --train_batch_size=2 \
 --num_train_epochs=10 \
 --max_train_steps=1501 \
 --checkpointing_steps=500 \
 --gradient_accumulation_steps=1\
 --gradient_checkpointing \
 --learning_rate=5e-6 \
 --use_8bit_adam \
 --report_to='wandb' \
 --validation_prompt="" \
 --mixed_precision='bf16' \
