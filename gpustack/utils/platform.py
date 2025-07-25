from enum import Enum
import os
import platform
import logging
import re
import subprocess
import threading

from gpustack.utils.command import is_command_available
from gpustack.schemas.workers import VendorEnum

logger = logging.getLogger(__name__)


def system() -> str:
    return platform.uname().system.lower()


def get_native_arch() -> str:
    system = platform.system()
    if system == "Windows":
        import pythoncom

        if threading.current_thread() is not threading.main_thread():
            pythoncom.CoInitialize()

        # Windows emulation will mask the native architecture
        # https://learn.microsoft.com/en-us/windows/arm/apps-on-arm-x86-emulation
        try:
            import wmi

            c = wmi.WMI()
            processor_info = c.Win32_Processor()
            arch_num = processor_info[0].Architecture

            # https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-processor
            arch_map = {
                0: 'x86',
                1: 'MIPS',
                2: 'Alpha',
                3: 'PowerPC',
                5: 'ARM',
                6: 'ia64',
                9: 'AMD64',
                12: 'ARM64',
            }

            arch = arch_map.get(arch_num, 'unknown')
            if arch != 'unknown':
                return arch.lower()
        except Exception as e:
            logger.warning(f"Failed to get native architecture from WMI, {e}")
        finally:
            if threading.current_thread() is not threading.main_thread():
                pythoncom.CoUninitialize()

    return platform.machine().lower()


def arch() -> str:
    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "i386": "386",
        "i686": "386",
        "arm64": "arm64",
        "aarch64": "arm64",
        "armv7l": "arm",
        "arm": "arm",
        "ppc64le": "ppc64le",
        "s390x": "s390x",
        "x86": "x86",
        "mips": "mips",
        "alpha": "alpha",
        "powerpc": "powerpc",
        "ia64": "ia64",
    }
    return arch_map.get(get_native_arch(), "unknown")


class DeviceTypeEnum(str, Enum):
    CUDA = "cuda"
    NPU = "npu"
    MPS = "mps"
    ROCM = "rocm"
    MUSA = "musa"
    DCU = "dcu"
    COREX = "corex"
    MLU = "mlu"


def device() -> str:
    """
    Returns the customized device type. This is similar to the device types in PyTorch but includes some additional types. Examples include:
    - cuda
    - musa
    - npu
    - mps
    - rocm
    - dcu
    - iluvatar
    - mlu
    - etc.
    """
    if (
        is_command_available("nvidia-smi")
        or os.path.exists("/usr/local/cuda")
        or os.path.exists("C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA")
    ):
        return DeviceTypeEnum.CUDA.value

    if (
        is_command_available("mthreads-gmi")
        or os.path.exists("/usr/local/musa")
        or os.path.exists("/opt/musa")
    ):
        return DeviceTypeEnum.MUSA.value

    if is_command_available("npu-smi") or os.path.exists(
        "/usr/local/Ascend/ascend-toolkit"
    ):
        return DeviceTypeEnum.NPU.value

    if system() == "darwin" and arch() == "arm64":
        return DeviceTypeEnum.MPS.value

    if is_command_available("hy-smi") or os.path.exists("/opt/dtk"):
        return DeviceTypeEnum.DCU.value

    if is_command_available("rocm-smi") or os.path.exists(
        "C:\\Program Files\\AMD\\ROCm"
    ):
        return DeviceTypeEnum.ROCM.value

    if is_command_available("ixsmi"):
        return DeviceTypeEnum.COREX.value

    if is_command_available("cnmon"):
        return DeviceTypeEnum.MLU.value

    return ""


def device_type_from_vendor(vendor: VendorEnum) -> str:
    mapping = {
        VendorEnum.NVIDIA.value: DeviceTypeEnum.CUDA.value,
        VendorEnum.Huawei.value: DeviceTypeEnum.NPU.value,
        VendorEnum.Apple.value: DeviceTypeEnum.MPS.value,
        VendorEnum.AMD.value: DeviceTypeEnum.ROCM.value,
        VendorEnum.Hygon.value: DeviceTypeEnum.DCU.value,
        VendorEnum.MTHREADS.value: DeviceTypeEnum.MUSA.value,
        VendorEnum.Iluvatar.value: DeviceTypeEnum.COREX.value,
        VendorEnum.Cambricon.value: DeviceTypeEnum.MLU.value,
    }

    return mapping.get(vendor, "")


def get_cuda_version() -> str:
    """
    Returns the CUDA toolkit version installed on the system.
    """
    if os.environ.get("CUDA_VERSION"):
        return os.environ["CUDA_VERSION"]

    try:
        import torch

        if torch.cuda.is_available():
            return torch.version.cuda
    except ImportError:
        pass

    if is_command_available("nvcc"):
        try:
            output = subprocess.check_output(["nvcc", "--version"], encoding="utf-8")
            match = re.search(r"release (\d+\.\d+),", output)
            if match:
                return match.group(1)
        except Exception as e:
            logger.error(f"Error running nvcc: {e}")
    return ""


def get_cann_version() -> str:
    """
    Returns the CANN version installed on the system.
    """

    env_cann_version = os.getenv("CANN_VERSION", "")
    if env_cann_version:
        return env_cann_version

    try:
        # Borrowed from https://gitee.com/ascend/pytorch/blob/master/test/npu/test_cann_version.py.
        import torch  # noqa: F401
        import torch_npu  # noqa: F401
        from torch_npu.utils.collect_env import (
            get_cann_version as get_cann_version_from_env,
        )
        from torch_npu.npu.utils import get_cann_version

        cann_version = get_cann_version_from_env()
        if cann_version:
            return cann_version.lower()
        cann_version = get_cann_version()
        if cann_version:
            return cann_version.lower()
    except ImportError:
        pass

    return ""


def get_cann_chip() -> str:
    """
    Returns the CANN chip version installed on the system.
    """

    env_cann_chip = os.getenv("CANN_CHIP", "")
    if env_cann_chip:
        return env_cann_chip

    try:
        # Borrowed from https://gitee.com/ascend/pytorch/blob/master/test/npu/test_soc_version.py.
        import torch  # noqa: F401
        import torch_npu  # noqa: F401
        from torch_npu.npu.utils import get_soc_version

        cann_soc_version = get_soc_version()
        # FIXME: Improve the SoC version list,
        # extract from MindIE ATB models: examples/models/atb_speed_sdk/atb_speed/common/launcher/npu.py.
        if cann_soc_version in (100, 101, 102, 103, 104, 200, 201, 202, 203, 204, 205):
            return "310p"
    except ImportError:
        pass

    return ""
