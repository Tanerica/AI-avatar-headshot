# Command to run the Python script
python train.py \
    --pretrained_model_name_or_path='SG161222/RealVisXL_V5.0' \
    --input_images "/workspace/Data/Ali/" \
    --output_dir='/workspace/output_cog/Ali/'\
    --seed 62 \
    --is_sdxl \
    --lora_lr=1e-4 \
    --lora_rank=48 \
    --resolution 768 \
    --train_batch_size 2 \
    --num_train_epochs 10 \
    --max_train_steps 1500 \
    --unet_learning_rate 1e-6  \
    --lr_scheduler "constant" \
    --lr_warmup_steps 100 \
    --token_string "ali01"\
    --caption_prefix "a portrait of " \
    --crop_based_on_salience True \
    --class_name 'man'\