# Requirements

Install mseg module (only works in Linux or MacOS), then install our requirements

```
pip install -e mseg
pip install -r requirements.txt
pip install git+https://github.com/openai/CLIP.git
```
# Usage
To train on cluster.
```
sbatch train_script_on_hpc.sh
```
This essentially runs the python script `train.py`.

To evaluate the trained model: `demo.ipynb`.

## Data Notes

We used MSeg. \
The semantic labels outputs corresponds to the `universal` column in `mseg-api/mseg/class_remapping_files/MSeg_master.tsv`

The datasets such as `COCOPanoptic` and `ADE20K` must lie within the folder `data/mseg_dataset/`

## DPT notes

### What is ViTWrapper

To make ViT work with arbitrary image size as input, made these changes during inference for each input image x:

1. Change attribute `image_size` (assumes H = W = `image_size`) of the ViT model. This is necessary to bypass the assert check `self.image_size == h == w` in `VisionTransformer._process_input(x)`.
2. Interpolate the learned position embedding by using their helper function `interpolate_embeddings` in `torchvision/models/vision_transformer.py`
   Link: https://github.com/pytorch/vision/blob/main/torchvision/models/vision_transformer.py#L268

### How to use DPT for LSeg

To use DPT as an pixel-wise encoder. Initialize it with this, where `C` is the desired multimodal embedding dimension. \
`model = DPT(head=nn.Identity(), output_feature_dim=C)`
