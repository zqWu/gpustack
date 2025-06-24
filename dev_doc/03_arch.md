# refer
- https://docs.gpustack.ai/latest/architecture/

# 组件 & 职责

## Server
- APIServer = restful / authentication / authorization
- Scheduler = 确定把 which model 放到 which worker上
- ModelController = rollout & scaling model instance
- HTTPProxy = 路由API到workers

## Worker
- running inference server for model instances assigned to the worker
- reporting status
- routes inference api requests to backend inference server

## sql database
- 默认 sqlite
- 已测试 mysql8

## InferenceServer
- llama-box
- vllm
- Ascend MindIE
- vox-box

## RPCServer
- 是 llama-box backend, 实测可以去掉

## Ray Head/worker
- vllm 跨节点部署时, 需要 Ray集群
  - vllm 参数: distributed_executor_backend
  - vllm 不跨节点多卡部署时, 默认使用 multiprocessing, 更轻量级
