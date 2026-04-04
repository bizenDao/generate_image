FROM bizenyakiko/genai-base:1.1

# Install ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI && \
    cd /ComfyUI && \
    pip install -r requirements.txt

# Install custom nodes
RUN cd /ComfyUI/custom_nodes && \
    git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git && \
    git clone https://github.com/ltdrdata/ComfyUI-Manager.git && \
    git clone https://github.com/city96/ComfyUI-GGUF.git

# Install node dependencies
RUN cd /ComfyUI/custom_nodes/ComfyUI_IPAdapter_plus && \
    pip install -r requirements.txt || true && \
    cd /ComfyUI/custom_nodes/ComfyUI-GGUF && \
    pip install -r requirements.txt || true

# Install handler dependencies (huggingface_hub must be installed before model downloads)
RUN pip install runpod websocket-client Pillow "huggingface_hub[hf_transfer]"

# Download FLUX.1 dev fp8 model
RUN mkdir -p /ComfyUI/models/diffusion_models && \
    python -m huggingface_hub.commands.huggingface_cli download Comfy-Org/flux1-dev \
    flux1-dev-fp8.safetensors \
    --local-dir /ComfyUI/models/diffusion_models

# Download text encoders
RUN mkdir -p /ComfyUI/models/text_encoders && \
    python -m huggingface_hub.commands.huggingface_cli download Comfy-Org/flux_text_encoders \
    t5xxl_fp8_e4m3fn.safetensors \
    clip_l.safetensors \
    --local-dir /ComfyUI/models/text_encoders

# Download VAE
RUN mkdir -p /ComfyUI/models/vae && \
    python -m huggingface_hub.commands.huggingface_cli download black-forest-labs/FLUX.1-dev \
    ae.safetensors \
    --local-dir /ComfyUI/models/vae

# Download CLIP Vision for IP-Adapter
RUN mkdir -p /ComfyUI/models/clip_vision && \
    python -m huggingface_hub.commands.huggingface_cli download Comfy-Org/sigclip_vision_384 \
    sigclip_vision_patch14_384.safetensors \
    --local-dir /ComfyUI/models/clip_vision

# Download IP-Adapter model for FLUX
RUN mkdir -p /ComfyUI/models/ipadapter && \
    python -m huggingface_hub.commands.huggingface_cli download InstantX/FLUX.1-dev-IP-Adapter \
    ip-adapter.bin \
    --local-dir /ComfyUI/models/ipadapter && \
    mv /ComfyUI/models/ipadapter/ip-adapter.bin /ComfyUI/models/ipadapter/ip-adapter_flux.safetensors

# Copy files
COPY handler.py /handler.py
COPY flux_ipadapter_api.json /flux_ipadapter_api.json
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Set environment
ENV HF_HUB_ENABLE_HF_TRANSFER=1

ENTRYPOINT ["/entrypoint.sh"]
