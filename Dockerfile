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

# Install handler dependencies
RUN pip install runpod websocket-client Pillow

# Download FLUX.1 dev fp8 model (public)
RUN mkdir -p /ComfyUI/models/diffusion_models && \
    wget -q https://huggingface.co/Comfy-Org/flux1-dev/resolve/main/flux1-dev-fp8.safetensors \
    -O /ComfyUI/models/diffusion_models/flux1-dev-fp8.safetensors

# Download text encoders (ungated mirror: comfyanonymous)
RUN mkdir -p /ComfyUI/models/text_encoders && \
    wget -q https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/t5xxl_fp8_e4m3fn.safetensors \
    -O /ComfyUI/models/text_encoders/t5xxl_fp8_e4m3fn.safetensors && \
    wget -q https://huggingface.co/comfyanonymous/flux_text_encoders/resolve/main/clip_l.safetensors \
    -O /ComfyUI/models/text_encoders/clip_l.safetensors

# Download VAE (ungated mirror: camenduru)
RUN mkdir -p /ComfyUI/models/vae && \
    wget -q https://huggingface.co/camenduru/FLUX.1-dev-ungated/resolve/main/ae.safetensors \
    -O /ComfyUI/models/vae/ae.safetensors

# Download CLIP Vision for IP-Adapter (public)
RUN mkdir -p /ComfyUI/models/clip_vision && \
    wget -q https://huggingface.co/Comfy-Org/sigclip_vision_384/resolve/main/sigclip_vision_patch14_384.safetensors \
    -O /ComfyUI/models/clip_vision/sigclip_vision_patch14_384.safetensors

# Download IP-Adapter model for FLUX (public)
RUN mkdir -p /ComfyUI/models/ipadapter && \
    wget -q https://huggingface.co/InstantX/FLUX.1-dev-IP-Adapter/resolve/main/ip-adapter.bin \
    -O /ComfyUI/models/ipadapter/ip-adapter_flux.bin

# Copy files
COPY handler.py /handler.py
COPY flux_ipadapter_api.json /flux_ipadapter_api.json
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
