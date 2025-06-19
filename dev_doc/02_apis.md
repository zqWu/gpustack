
# 启动模型
PUT http://115.190.108.165:9055/v1/models/1
{
    "source": "local_path",
    "huggingface_repo_id": null,
    "huggingface_filename": null,
    "ollama_library_model_name": null,
    "model_scope_model_id": null,
    "model_scope_file_path": null,
    "local_path": "/data/models/Qwen3-0.6B",
    "name": "qwen3-0.6b",
    "description": null,
    "meta": {},
    "replicas": 1,
    "categories": [
        "llm"
    ],
    "embedding_only": false,
    "image_only": false,
    "reranker": false,
    "speech_to_text": false,
    "text_to_speech": false,
    "placement_strategy": "spread",
    "cpu_offloading": false,
    "distributed_inference_across_workers": true,
    "worker_selector": {},
    "gpu_selector": {
        "gpu_ids": [
            "iv-ydjb0dsmww5i3z2xkzwa:cuda:4"
        ]
    },
    "backend": "vllm",
    "backend_version": null,
    "backend_parameters": [],
    "env": {},
    "restart_on_error": true,
    "distributable": false
}
