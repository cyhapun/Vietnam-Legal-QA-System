# fix-vercel-services-framework-config Specification

## Purpose
Đảm bảo cấu hình triển khai Vercel (`vercel.json`) tuân thủ chuẩn `services` hiện hành của Vercel CLI, đồng thời chỉ định tường minh framework cho cả frontend (`nextjs`) và backend (`fastapi`) nhằm ngăn chặn xung đột nhận diện đa framework (`MULTIPLE_FRAMEWORKS_SERVICE`).

## Requirements

### Requirement: Modern Vercel Services Configuration
Tệp cấu hình `vercel.json` SHALL sử dụng thuộc tính `services` thay cho `experimentalServices`.

#### Scenario: Vercel CLI parses configuration
- **WHEN** Vercel CLI đọc tệp `vercel.json`
- **THEN** không xuất hiện cảnh báo `The 'experimentalServices' property is deprecated`
- **AND THEN** các dịch vụ `frontend` và `backend` được cấu hình dưới khóa `services`.

### Requirement: Explicit Backend Framework Definition
Dịch vụ `backend` trong `vercel.json` SHALL định nghĩa thuộc tính `"framework": "fastapi"`.

#### Scenario: Vercel builds backend service
- **WHEN** Vercel tiến hành build service `backend`
- **THEN** Vercel áp dụng cơ chế build Python FastAPI serverless function
- **AND THEN** không phát sinh lỗi xung đột `[MULTIPLE_FRAMEWORKS_SERVICE]`.
