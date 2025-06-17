import sys
from gpustack.main import main

if __name__ == '__main__':
    # 启动参数中配置
    # start --data-dir=debug_data_dir --port=9055
    # 原命令 gpustack start --key=val
    sys.exit(main())
