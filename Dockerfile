FROM bizenyakiko/genai-base:1.1

# Install ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI && \
    cd /ComfyUI && \
    pip install -r requirements.txt

# Install ComfyUI-Manager
RUN cd /ComfyUI/custom_nodes && \
    git clone https://github.com/Comfy-Org/ComfyUI-Manager.git && \
    cd ComfyUI-Manager && \
    pip install -r requirements.txt || true

# Install handler dependencies
RUN pip install runpod websocket-client Pillow

# Download Pony Diffusion V6 XL (~6.5GB, public)
RUN mkdir -p /ComfyUI/models/checkpoints && \
    wget -q https://huggingface.co/AstraliteHeart/pony-diffusion-v6/resolve/main/v6.safetensors \
    -O /ComfyUI/models/checkpoints/ponyDiffusionV6XL.safetensors

# Copy files
COPY handler.py /handler.py
COPY pony_v6_api.json /pony_v6_api.json
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
