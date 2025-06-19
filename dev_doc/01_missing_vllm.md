# 问题
debug启动后, 在ui界面进行操作:拉起一个llm, 报错如下, 缺少 vllm执行环境

```text
gpustack.worker.backends.base - INFO - Preparing model files...
gpustack.worker.backends.base - INFO - Model files are ready.
gpustack.utils.profiling - DEBUG - __init__ execution time: 0.01697683334350586 seconds
gpustack.utils.hub - DEBUG - Derived max model length: 40960
gpustack.worker.backends.vllm - INFO - Starting vllm server
gpustack.worker.backends.vllm - DEBUG - Run vllm with arguments: serve /data/models/Qwen3-0.6B --max-model-len 8192 --host 0.0.0.0 --port 40032 --served-model-name qwen3-0.6b
gpustack.worker.backends.vllm - ERROR - Failed to run the vllm server: [Errno 2] No such file or directory: '/data/project/wuzhongqin/.conda/envs/gpustack/bin/vllm'
```

## 对比 gpustack 容器
- 里面包含了 vllm的执行环境
```bash
root@H20-115:/# whereis gpustack
gpustack: /usr/local/bin/gpustack

root@H20-115:/# whereis vllm
vllm: /usr/local/bin/vllm
```

## 分析 Dockerfile
```
ARG VLLM_VERSION=0.9.1

RUN gpustack download-tools
```

debug `gpustack download-tools`, 最后结果是下载了一些bin, 放到了这里
- gpustack/third_party/bin/
  - fastfetch/fastfetch
  - gguf-parser/gguf-parser
  - llama-box/llama-box-rpc-server llama-box-linux-amd64-cuda

- 并没有下载 vllm

## 分析安装脚本
- https://github.com/gpustack/gpustack/blob/main/install.sh
  - 725/733 可以看到 在 amd64 + linux系统中, 安装了 default_package_spec="gpustack[all]"

- 在gpustack/pyproject.toml中, 可以看到以下内容
  - all = ["vllm", "mistral_common", "bitsandbytes", "timm", "vox-box"]
### 结论: 安装脚步(linux+amd64, 非docker)是将 vllm一并进行了安装

## 再分析 Dockerfile
- 也有 WHEEL_PACKAGE="$(ls /workspace/gpustack/dist/*.whl)[all]";

```bash
docker build -t gpustack:debug_v1 .

docker run -ti --rm --gpus all --entrypoint /bin/bash gpustack:debug_v1

which vllm
# 输出 /usr/local/bin/vllm

vllm --version
# 0.9.1 <======== 这个是 Dockerfile指定的 VLLM版本
```
