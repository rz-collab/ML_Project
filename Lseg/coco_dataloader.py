import os
import torch
from torch.utils.data import Dataset
from torchvision import transforms
from PIL import Image
import numpy as np
import json


def rgb_to_segment_id(rgb_image, num_classes=201):
    rgb = np.array(rgb_image)
    segment_id = (
        rgb[:, :, 0].astype(np.uint32) * 256 * 256
        + rgb[:, :, 1].astype(np.uint32) * 256
        + rgb[:, :, 2].astype(np.uint32)
    )
    segment_id = segment_id % num_classes
    return segment_id


def one_hot_encode_from_segment_id(segment_id, num_classes=201, target_classes=201):
    segment_id = torch.tensor(segment_id.astype(np.int64), dtype=torch.long)  # Convert to tensor
    unique_segment_ids = np.unique(segment_id)
    print(f"Unique segment IDs: {unique_segment_ids}")
    print(f"Number of unique segment IDs: {len(unique_segment_ids)}")
    try:
        y_one_hot = torch.nn.functional.one_hot(segment_id, num_classes=num_classes)
    except Exception as e:
        print(f"Error during one-hot encoding: {e}")
        raise  # [H, W, num_classes]
    y_one_hot = y_one_hot.permute(2, 0, 1).float()  # [1, num_classes, H, W]

    print(f"One-hot encoded mask unique values (first image): {torch.unique(y_one_hot[0])}")

    if target_classes > num_classes:
        padding = torch.zeros(
            (y_one_hot.size(0), target_classes - num_classes, y_one_hot.size(2), y_one_hot.size(3)),
            device=y_one_hot.device,
        )
        y_one_hot = torch.cat([y_one_hot, padding], dim=1)
    elif target_classes < num_classes:
        y_one_hot = y_one_hot[:, :target_classes, :, :]

    return y_one_hot


class COCOPanopticDataset(Dataset):
    def __init__(
        self,
        images_dir,
        panoptic_dir,
        annotations_file,
        transform=None,
        target_transform=None,
        num_classes=201,
        resize=(256, 256),
    ):
        self.images_dir = images_dir
        self.panoptic_dir = panoptic_dir
        self.transform = transform
        self.target_transform = target_transform
        self.num_classes = num_classes
        self.resize = resize
        with open(annotations_file, "r") as f:
            self.annotations = json.load(f)
        self.image_id_to_ann = {ann["image_id"]: ann for ann in self.annotations["annotations"]}
        self.images = self.annotations["images"]

    def __len__(self):
        return len(self.images)

    def __getitem__(self, idx):
        img_info = self.images[idx]
        img_id = img_info["id"]
        img_filename = img_info["file_name"]
        img_path = os.path.join(self.images_dir, img_filename)

        try:
            image = Image.open(img_path).convert("RGB")
        except Exception as e:
            raise

        ann = self.image_id_to_ann.get(img_id, None)
        if ann is None:
            raise ValueError(f"No annotation found for image_id {img_id}")

        panoptic_filename = ann["file_name"]
        panoptic_path = os.path.join(self.panoptic_dir, panoptic_filename)

        if not os.path.exists(panoptic_path):
            raise FileNotFoundError(f"Panoptic mask not found: {panoptic_filename}")

        try:
            panoptic_image = Image.open(panoptic_path)
        except Exception as e:
            raise
        # Resize panoptic image to match the image size
        panoptic_image = panoptic_image.resize(self.resize, Image.NEAREST)
        segment_id = rgb_to_segment_id(panoptic_image)
        print(f"segment_id: {segment_id}")

        # Directly convert segment_id to one-hot encoding
        y_one_hot = one_hot_encode_from_segment_id(
            segment_id, num_classes=self.num_classes, target_classes=self.num_classes
        )

        if self.transform:
            image = self.transform(image)

        if self.target_transform:
            y_one_hot = self.target_transform(y_one_hot)

        return image, y_one_hot


def load_coco_dataset(get_train: bool):
    """Default function that returns dataset and dataloader for COCOPanoptic"""

    H, W = 480, 480
    image_transforms = transforms.Compose(
        [
            transforms.Resize((H, W)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    if get_train is True:
        images_dir = "../data/COCOPanoptic/COCOPanoptic/images/train2017"
        panoptic_dir = "../data/COCOPanoptic/COCOPanoptic/annotations/panoptic_train2017"
        annotations_file = "../data/COCOPanoptic/COCOPanoptic/annotations/panoptic_train2017.json"
    else:
        # Get validation set
        # TODO: Verify this is the correct path
        images_dir = "../data/COCOPanoptic/COCOPanoptic/images/valid2017"
        panoptic_dir = "../data/COCOPanoptic/COCOPanoptic/annotations/panoptic_valid2017"
        annotations_file = "../data/COCOPanoptic/COCOPanoptic/annotations/panoptic_valid2017.json"

    dataset = COCOPanopticDataset(
        images_dir=images_dir,
        panoptic_dir=panoptic_dir,
        annotations_file=annotations_file,
        transform=image_transforms,
        num_classes=201,
    )

    return dataset