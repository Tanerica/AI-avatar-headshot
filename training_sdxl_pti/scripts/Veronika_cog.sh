# Command to run the Python script
python train.py \
    --pretrained_model_name_or_path='SG161222/RealVisXL_V5.0' \
    --input_images "/workspace/AI-avatar-headshot/Data/Veronika/" \
    --output_dir='/workspace/AI-avatar-headshot/output_cog/Veronika/'\
    --seed 62 \
    --is_sdxl \
    --lora_lr=1e-4 \
    --lora_rank=48 \
    --resolution 768 \
    --train_batch_size 3 \
    --num_train_epochs 10 \
    --max_train_steps 1500 \
    --unet_learning_rate 2e-6  \
    --lr_scheduler "constant" \
    --lr_warmup_steps 100 \
    --token_string "veronika01"\
    --caption_prefix "a portrait of " \
    --crop_based_on_salience True \
    --class_name 'woman'\