# 配置基本环境

```bash
conda create -n gpustack python=3.10 -y
conda activate gpustack

git clone https://github.com/gpustack/gpustack.git
cd gpustack

make install
make lint
make test
make build
```

# 进行debug
## 屏蔽原来的 gpustack

```bash
whereis gpustack
# 输出 /data/project/wuzhongqin/.conda/envs/gpustack/bin/gpustack


cd /data/project/wuzhongqin/.conda/envs/gpustack/bin/gpustack
mv gpustack _backup_gpustack
```

## 在 gpustack项目根目录下创建 debug.py

- 这个内容就是 原gpustack里面的内容

```python
import sys
from gpustack.main import main

if __name__ == '__main__':
    sys.exit(main())
```

## 配置pycharm
- start 选项见 gpustack/cmd/start.py
```
# 具体参数描述见 gpustack/cmd/start.py
start
--data-dir=debug_data_dir
--port=9055
--debug
--disable-rpc-servers
--database-url
mysql://root:my-secret-ab@120.132.117.123:9043/gpustack
```

![](./debug_config_pycharm.png)

# 关键代码
- 程序入口: gpustack/main.py
- server/server.py


## 手动安装 pip install vllm==0.9.1
```bash
conda activate gpustack
pip install vllm==0.9.1
```

# 问题与解决
## rpc_server启动报错: libcudart.so.12: cannot open shared object file
这个是子进程报错. 主进程中(运行于conda环境下), 能够正确的找到这些内容
```text
>>> import torch          
>>> torch.cuda.is_available()
True
>>> torch.version.cuda
'12.6'
```
找到当前环境的 .so
```bash
find $CONDA_PREFIX -name "libcudart.so.12" 2>/dev/null
/data/project/wuzhongqin/.conda/envs/gpustack/lib/python3.10/site-packages/nvidia/cuda_runtime/lib/libcudart.so.12
```
配置到环境中去 ===> 无效，问题依旧
见 rpc_server.py line83, 即使传递最原始的字符串也不行

启动时关闭 rpc_server 
