INSTANCE_DIR="/workspace/kohya-trainer/Ali_sd/instance/"  # Path to your instance images (personal images)
CLASS_DIR="/workspace/kohya-trainer/Ali_sd/class/"        # Path to regularization images (optional)
OUTPUT_DIR="/workspace/output_tandb"            # Directory to save trained model
PRETRAINED_MODEL="SG161222/Realistic_Vision_V2.0"
# Run DreamBooth training
# chú ý cách đặt tên folder instance data and training data (==). Kohya ko sử dụng instance prompt và class prompt parameters như diffusers. 
# Trong folder train_data_dir —> có thể có nhiều hơn 1 folder instance_images —> đặt tên theo cú pháp NumberRepeat_keyword classname —> 100_t4nngo face man
# Trong folder reg_data_dir —> có thể có nhiều hơn 1 folder class_images —> đặt tên theo cú pháp NumberRepeat_classname —> 20_face man
python train_db.py \
  --pretrained_model_name_or_path=$PRETRAINED_MODEL \
  --output_dir=$OUTPUT_DIR \
  --train_batch_size=1 \
  --max_train_steps=1500 \
  --learning_rate=5e-6 \
  --mixed_precision="bf16" \
  --train_data_dir=$INSTANCE_DIR \
  --resolution=768 \
  --prior_loss_weight=1.0 \
  --reg_data_dir=$CLASS_DIR \
  --sample_sampler="ddim" \
  --use_8bit_adam \
  --seed=62\
  --gradient_checkpointing\
  --save_model_as='safetensors'\
  --caption_extension='.txt'