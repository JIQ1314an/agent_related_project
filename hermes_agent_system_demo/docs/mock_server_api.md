# 服务器运维状态查询 API 文档

本文档描述如何查询内部数据中心服务器的状态指标。

## 接口地址：GetServerMetrics

**功能描述**：根据传入的服务器 `server_id`，查询其 CPU 使用率、内存使用率以及磁盘空间。

**请求参数 (JSON)**：
- `server_id` (string, 必填): 服务器唯一标识符（例如: "srv-bj-001"）
- `metric_type` (string, 选填): 查询的指标类型，可选值为 "all", "cpu", "memory"。默认为 "all"。

**返回参数 (JSON)**：
```json
{
  "status": "success",
  "data": {
    "server_id": "srv-bj-001",
    "cpu_usage": "78.5%",
    "memory_usage": "62.1%",
    "disk_free_gb": 120,
    "health_status": "WARNING"
  }
}