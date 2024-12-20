# Have SwinIR upsample
# Have BLIP auto caption
# Have CLIPSeg auto mask concept

import struct
import gc
import fnmatch
import mimetypes
import os
import re
import shutil
import tarfile
from pathlib import Path
from typing import List, Literal, Optional, Tuple, Union
from zipfile import ZipFile

import cv2
import mediapipe as mp
import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageFilter, ImageOps
from tqdm import tqdm
from transformers import (
    BlipForConditionalGeneration,
    BlipProcessor,
    CLIPSegForImageSegmentation,
    CLIPSegProcessor,
    Swin2SRForImageSuperResolution,
    Swin2SRImageProcessor,
)

MODEL_PATH = "/data/cache"
# TEMP_OUT_DIR = "/data/temp/"
# TEMP_IN_DIR = "./temp_in/"


def preprocess(
    # input_zip_path: Path,
    input_path: Path,
    output_dir: Path,
    caption_text: str,
    token_string: str,
    class_name: str,
    mask_target_prompts: str,
    target_size: int,
    crop_based_on_salience: bool,
    use_face_detection_instead: bool,
    temp: float,
    substitution_tokens: List[str],
) -> Path:

    load_and_save_masks_and_captions(
        input_dir=input_path,
        caption_text=caption_text + " " + token_string + " " + class_name,
        mask_target_prompts=mask_target_prompts,
        target_size=target_size,
        crop_based_on_salience=crop_based_on_salience,
        use_face_detection_instead=use_face_detection_instead,
        temp=temp,
        substitution_tokens=substitution_tokens,
    )

    return Path(input_path)


@torch.no_grad()
@torch.cuda.amp.autocast()
def swin_ir_sr(
    images: List[Image.Image],
    model_id: Literal[
        "caidas/swin2SR-classical-sr-x2-64",
        "caidas/swin2SR-classical-sr-x4-48",
        "caidas/swin2SR-realworld-sr-x4-64-bsrgan-psnr",
    ] = "caidas/swin2SR-realworld-sr-x4-64-bsrgan-psnr",
    target_size: Optional[Tuple[int, int]] = None,
    device=torch.device("cuda:0" if torch.cuda.is_available() else "cpu"),
    **kwargs,
) -> List[Image.Image]:
    """
    Upscales images using SwinIR. Returns a list of PIL images.
    If the image is already larger than the target size, it will not be upscaled
    and will be returned as is.

    """

    model = Swin2SRForImageSuperResolution.from_pretrained(
        model_id, cache_dir=MODEL_PATH
    ).to(device)
    processor = Swin2SRImageProcessor()

    out_images = []

    for image in tqdm(images):
        ori_w, ori_h = image.size
        if target_size is not None:
            if ori_w >= target_size[0] and ori_h >= target_size[1]:
                out_images.append(image)
                continue

        inputs = processor(image, return_tensors="pt").to(device)
        with torch.no_grad():
            outputs = model(**inputs)

        output = (
            outputs.reconstruction.data.squeeze().float().cpu().clamp_(0, 1).numpy()
        )
        output = np.moveaxis(output, source=0, destination=-1)
        output = (output * 255.0).round().astype(np.uint8)
        output = Image.fromarray(output)

        out_images.append(output)

    return out_images


@torch.no_grad()
@torch.cuda.amp.autocast()
def clipseg_mask_generator(
    images: List[Image.Image],
    target_prompts: Union[List[str], str],
    model_id: Literal[
        "CIDAS/clipseg-rd64-refined", "CIDAS/clipseg-rd16"
    ] = "CIDAS/clipseg-rd64-refined",
    device=torch.device("cuda:0" if torch.cuda.is_available() else "cpu"),
    bias: float = 0.01,
    temp: float = 1.0,
    **kwargs,
) -> List[Image.Image]:
    """
    Returns a greyscale mask for each image, where the mask is the probability of the target prompt being present in the image
    """

    if isinstance(target_prompts, str):
        print(
            f'Warning: only one target prompt "{target_prompts}" was given, so it will be used for all images'
        )

        target_prompts = [target_prompts] * len(images)

    processor = CLIPSegProcessor.from_pretrained(model_id, cache_dir=MODEL_PATH)
    model = CLIPSegForImageSegmentation.from_pretrained(
        model_id, cache_dir=MODEL_PATH
    ).to(device)

    masks = []

    for image, prompt in tqdm(zip(images, target_prompts)):
        original_size = image.size

        inputs = processor(
            text=prompt,
            images=image,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        ).to(device)

        outputs = model(**inputs)

        logits = outputs.logits
        probs = torch.sigmoid(logits) * 255

        # make mask greyscale
        mask = Image.fromarray(probs.cpu().numpy().astype(np.uint8)).convert("L")

        # resize mask to original size
        mask = mask.resize(original_size)

        masks.append(mask)

    return masks


@torch.no_grad()
def blip_captioning_dataset(
    images: List[Image.Image],
    text: Optional[str] = None,
    model_id: Literal[
        "Salesforce/blip-image-captioning-large",
        "Salesforce/blip-image-captioning-base",
    ] = "Salesforce/blip-image-captioning-large",
    device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
    substitution_tokens: Optional[List[str]] = None,
    **kwargs,
) -> List[str]:
    """
    Returns a list of captions for the given images
    """
    torch.manual_seed(42)
    processor = BlipProcessor.from_pretrained(model_id, cache_dir=MODEL_PATH)
    model = BlipForConditionalGeneration.from_pretrained(
        model_id, cache_dir=MODEL_PATH
    ).to(device)
    captions = []
    print(f"Input captioning text: {text}")
    for image in tqdm(images):
        inputs = processor(image, text=text, return_tensors="pt").to("cuda")
        out = model.generate(
            **inputs, max_length=150, do_sample=True, top_k=50, temperature=0.7
        )
        caption = processor.decode(out[0], skip_special_tokens=True)

        # BLIP 2 lowercases all caps tokens. This should properly replace them w/o messing up subwords. I'm sure there's a better way to do this.
        for token in substitution_tokens:
            print(token)
            sub_cap = " " + caption + " "
            print(sub_cap)
            sub_cap = sub_cap.replace(" " + token.lower() + " ", " " + token + " ")
            caption = sub_cap.strip()

        captions.append(caption)
    print("Generated captions", captions)
    return captions


def face_mask_google_mediapipe(
    images: List[Image.Image], blur_amount: float = 0.0, bias: float = 50.0
) -> List[Image.Image]:
    """
    Returns a list of images with masks on the face parts.
    """
    mp_face_detection = mp.solutions.face_detection
    mp_face_mesh = mp.solutions.face_mesh

    face_detection = mp_face_detection.FaceDetection(
        model_selection=1, min_detection_confidence=0.1
    )
    face_mesh = mp_face_mesh.FaceMesh(
        static_image_mode=True, max_num_faces=1, min_detection_confidence=0.1
    )

    masks = []
    for image in tqdm(images):
        image_np = np.array(image)

        # Perform face detection
        results_detection = face_detection.process(image_np)
        ih, iw, _ = image_np.shape
        if results_detection.detections:
            for detection in results_detection.detections:
                bboxC = detection.location_data.relative_bounding_box

                bbox = (
                    int(bboxC.xmin * iw),
                    int(bboxC.ymin * ih),
                    int(bboxC.width * iw),
                    int(bboxC.height * ih),
                )

                # make sure bbox is within image
                bbox = (
                    max(0, bbox[0]),
                    max(0, bbox[1]),
                    min(iw - bbox[0], bbox[2]),
                    min(ih - bbox[1], bbox[3]),
                )

                print(bbox)

                # Extract face landmarks
                face_landmarks = face_mesh.process(
                    image_np[bbox[1] : bbox[1] + bbox[3], bbox[0] : bbox[0] + bbox[2]]
                ).multi_face_landmarks

                # https://github.com/google/mediapipe/issues/1615
                # This was def helpful
                indexes = [
                    10,
                    338,
                    297,
                    332,
                    284,
                    251,
                    389,
                    356,
                    454,
                    323,
                    361,
                    288,
                    397,
                    365,
                    379,
                    378,
                    400,
                    377,
                    152,
                    148,
                    176,
                    149,
                    150,
                    136,
                    172,
                    58,
                    132,
                    93,
                    234,
                    127,
                    162,
                    21,
                    54,
                    103,
                    67,
                    109,
                ]

                if face_landmarks:
                    mask = Image.new("L", (iw, ih), 0)
                    mask_np = np.array(mask)

                    for face_landmark in face_landmarks:
                        face_landmark = [face_landmark.landmark[idx] for idx in indexes]
                        landmark_points = [
                            (int(l.x * bbox[2]) + bbox[0], int(l.y * bbox[3]) + bbox[1])
                            for l in face_landmark
                        ]
                        mask_np = cv2.fillPoly(
                            mask_np, [np.array(landmark_points)], 255
                        )

                    mask = Image.fromarray(mask_np)

                    # Apply blur to the mask
                    if blur_amount > 0:
                        mask = mask.filter(ImageFilter.GaussianBlur(blur_amount))

                    # Apply bias to the mask
                    if bias > 0:
                        mask = np.array(mask)
                        mask = mask + bias * np.ones(mask.shape, dtype=mask.dtype)
                        mask = np.clip(mask, 0, 255)
                        mask = Image.fromarray(mask)

                    # Convert mask to 'L' mode (grayscale) before saving
                    mask = mask.convert("L")

                    masks.append(mask)
                else:
                    # If face landmarks are not available, add a black mask of the same size as the image
                    masks.append(Image.new("L", (iw, ih), 255))

        else:
            print("No face detected, adding full mask")
            # If no face is detected, add a white mask of the same size as the image
            masks.append(Image.new("L", (iw, ih), 255))

    return masks


def _crop_to_square(
    image: Image.Image, com: List[Tuple[int, int]], resize_to: Optional[int] = None
):
    cx, cy = com
    width, height = image.size
    if width > height:
        left_possible = max(cx - height / 2, 0)
        left = min(left_possible, width - height)
        right = left + height
        top = 0
        bottom = height
    else:
        left = 0
        right = width
        top_possible = max(cy - width / 2, 0)
        top = min(top_possible, height - width)
        bottom = top + width

    image = image.crop((left, top, right, bottom))

    if resize_to:
        image = image.resize((resize_to, resize_to), Image.Resampling.LANCZOS)

    return image


def _center_of_mass(mask: Image.Image):
    """
    Returns the center of mass of the mask
    """
    x, y = np.meshgrid(np.arange(mask.size[0]), np.arange(mask.size[1]))
    mask_np = np.array(mask) + 0.01
    x_ = x * mask_np
    y_ = y * mask_np

    x = np.sum(x_) / np.sum(mask_np)
    y = np.sum(y_) / np.sum(mask_np)

    return x, y

def orient_by_exif(pil_image: Image.Image):
    try:
        pil_image = ImageOps.exif_transpose(pil_image)
    except (TypeError, ValueError, struct.error):
        print("Failed to fix ORIENTATION")
        # TypeError: object of type 'IFDRational' has no len()
        # ValueError: cannot convert float NaN to integer
        if hasattr(pil_image, '_getexif') and pil_image._getexif() is not None:
            orientation = pil_image._getexif().get(0x0112, 1)
            if orientation == 3:
                pil_image = pil_image.transpose(Image.ROTATE_180)
            elif orientation == 6:
                pil_image = pil_image.transpose(Image.ROTATE_270)
            elif orientation == 8:
                pil_image = pil_image.transpose(Image.ROTATE_90)
    return pil_image


def load_and_save_masks_and_captions(
    input_dir: Union[str, List[str]],
    caption_text: Optional[str] = None,
    mask_target_prompts: Optional[Union[List[str], str]] = None,
    target_size: int = 1024,
    crop_based_on_salience: bool = True,
    use_face_detection_instead: bool = False,
    temp: float = 1.0,
    n_length: int = -1,
    substitution_tokens: Optional[List[str]] = None,
):
    """
    Loads images from the given files, generates masks for them, and saves the masks and captions and upscale images
    to output dir. If mask_target_prompts is given, it will generate kinda-segmentation-masks for the prompts and save them as well.

    Example:
    >>> x = load_and_save_masks_and_captions(
                files="./data/images",
                caption_text="a photo of",
                mask_target_prompts="cat",
                target_size=768,
                crop_based_on_salience=True,
                use_face_detection_instead=False,
                temp=1.0,
                n_length=-1,
            )
    """
    # load images
    if isinstance(input_dir, str):
        # check if it is a directory
        if os.path.isdir(input_dir):
            # get all the .png .jpg in the directory
            files = (
                _find_files("*.png", input_dir)
                + _find_files("*.jpg", input_dir)
                + _find_files("*.jpeg", input_dir)
            )

        if len(files) == 0:
            raise Exception(
                f"No files found in {files}. Either {files} is not a directory or it does not contain any .png or .jpg/jpeg files."
            )
        if n_length == -1:
            n_length = len(files)
        files = sorted(files)[:n_length]
        print(files)
    images = [orient_by_exif(Image.open(file).convert("RGB")) for file in files]

    # captions
    print(f"Generating {len(images)} captions...")
    if os.environ.get('DISABLE_AUTO_CAPTIONS', False):
        captions = [caption_text] * len(images)
        print("captions", captions)
    else:
        captions = blip_captioning_dataset(
            images, text=caption_text, substitution_tokens=substitution_tokens
        )

    if mask_target_prompts is None:
        mask_target_prompts = ""
        temp = 999

    print(f"Generating {len(images)} masks...")
    if not use_face_detection_instead:
        seg_masks = clipseg_mask_generator(
            images=images, target_prompts=mask_target_prompts, temp=temp
        )
    else:
        seg_masks = face_mask_google_mediapipe(images=images)

    # find the center of mass of the mask
    if crop_based_on_salience:
        coms = [_center_of_mass(mask) for mask in seg_masks]
    else:
        coms = [(image.size[0] / 2, image.size[1] / 2) for image in images]
    # based on the center of mass, crop the image to a square
    images = [
        _crop_to_square(image, com, resize_to=None) for image, com in zip(images, coms)
    ]

    print(f"Upscaling {len(images)} images...")
    # upscale images anyways
    images = swin_ir_sr(images, target_size=(target_size, target_size))
    images = [
        image.resize((target_size, target_size), Image.Resampling.LANCZOS)
        for image in images
    ]

    seg_masks = [
        _crop_to_square(mask, com, resize_to=target_size)
        for mask, com in zip(seg_masks, coms)
    ]

    data = []

    # iterate through the images, masks, and captions and add a row to the dataframe for each
    for idx, (image, mask, caption) in enumerate(zip(images, seg_masks, captions)):
        image_name = f"{idx}.src.png"
        mask_file = f"{idx}.mask.png"

        # save the image and mask files
        image.save(input_dir + image_name)
        mask.save(input_dir + mask_file)

        # add a new row to the dataframe with the file names and caption
        data.append(
            {"image_path": image_name, "mask_path": mask_file, "caption": caption},
        )
        # data.append(
        #     {"image_path": image_name, "caption": caption},
        # )

    df = pd.DataFrame(columns=["image_path", "mask_path", "caption"], data=data)
    # save the dataframe to a CSV file
    df.to_csv(os.path.join(input_dir, "captions.csv"), index=False)


def _find_files(pattern, dir="."):
    """Return list of files matching pattern in a given directory, in absolute format.
    Unlike glob, this is case-insensitive.
    """

    rule = re.compile(fnmatch.translate(pattern), re.IGNORECASE)
    return [os.path.join(dir, f) for f in os.listdir(dir) if rule.match(f)]
