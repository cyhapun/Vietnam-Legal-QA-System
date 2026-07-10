'use client';

import React, { useEffect, useState } from 'react';
import {
  BrainCircuit,
  Check,
  Database,
  FileCheck2,
  History,
  RefreshCw,
  RotateCcw,
  Save,
  Search,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Zap,
} from 'lucide-react';
import { AI_MODELS } from '@/lib/constants';
import { AISettings, DEFAULT_AI_SETTINGS } from '@/lib/ai-settings';
import { useAISettings } from '@/hooks/use-ai-settings';

const SYSTEM_FEATURES = [
  {
    icon: Search,
    title: 'Truy xuất tài liệu',
    status: 'Hybrid Search',
    description: 'Kết hợp tìm kiếm ngữ nghĩa và từ khóa, sau đó lọc theo lĩnh vực pháp luật.',
  },
  {
    icon: SlidersHorizontal,
    title: 'Reranking',
    status: 'Theo cấu hình backend',
    description: 'Sắp xếp lại các điều khoản theo mức độ liên quan trước khi gửi cho mô hình.',
  },
  {
    icon: Sparkles,
    title: 'Query Rewriter',
    status: 'Theo cấu hình backend',
    description: 'Chuẩn hóa câu hỏi và có thể tách câu hỏi phức tạp thành nhiều truy vấn pháp lý.',
  },
  {
    icon: FileCheck2,
    title: 'Trích dẫn pháp lý',
    status: 'Bắt buộc',
    description: 'Chỉ hiển thị các căn cứ được mô hình trích dẫn bằng ID điều khoản hợp lệ.',
  },
  {
    icon: History,
    title: 'Bộ nhớ hội thoại',
    status: 'Đang bật',
    description: 'Sử dụng lịch sử gần nhất và bản tóm tắt phiên để giữ ngữ cảnh trao đổi.',
  },
  {
    icon: Zap,
    title: 'Semantic Cache',
    status: 'Theo cấu hình backend',
    description: 'Tái sử dụng câu trả lời cho truy vấn tương đồng và tự vô hiệu hóa khi tài liệu đổi.',
  },
  {
    icon: Database,
    title: 'Kho dữ liệu',
    status: 'PostgreSQL + Qdrant',
    description: 'PostgreSQL lưu metadata; Qdrant lưu vector dense và sparse phục vụ truy xuất.',
  },
  {
    icon: ShieldCheck,
    title: 'Thông tin nhạy cảm',
    status: 'Được bảo vệ',
    description: 'API key, DSN và khóa Qdrant chỉ được cấu hình qua biến môi trường phía server.',
  },
];

export default function SystemSettingsTab() {
  const { settings, setSettings, resetSettings, isLoaded } = useAISettings();
  const [draft, setDraft] = useState<AISettings>(DEFAULT_AI_SETTINGS);
  const [section, setSection] = useState<'basic' | 'advanced'>('basic');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (isLoaded) setDraft(settings);
  }, [isLoaded, settings]);

  const updateDraft = <K extends keyof AISettings,>(key: K, value: AISettings[K]) => {
    setDraft(current => ({ ...current, [key]: value }));
    setSaved(false);
  };

  const handleSave = () => {
    setSettings(draft);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 2000);
  };

  const handleReset = () => {
    resetSettings();
    setDraft(DEFAULT_AI_SETTINGS);
    setSaved(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-indigo-600 dark:text-indigo-400 mb-2">
            <BrainCircuit className="w-5 h-5" />
            <span className="text-xs font-bold uppercase tracking-widest">AI Configuration</span>
          </div>
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">Cấu hình AI & Tìm kiếm</h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1 max-w-2xl">
            Điều chỉnh cấu hình mặc định dùng cho các câu hỏi mới trên trình duyệt này.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleReset}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-slate-700 rounded-xl hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            Mặc định
          </button>
          <button
            type="button"
            onClick={handleSave}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition-colors shadow-sm"
          >
            {saved ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
            {saved ? 'Đã lưu' : 'Lưu cấu hình'}
          </button>
        </div>
      </div>

      <div className="inline-flex p-1 bg-gray-100 dark:bg-slate-800 rounded-xl">
        <button
          type="button"
          onClick={() => setSection('basic')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${section === 'basic' ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-sm' : 'text-gray-500 dark:text-gray-400'}`}
        >
          Cơ bản
        </button>
        <button
          type="button"
          onClick={() => setSection('advanced')}
          className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${section === 'advanced' ? 'bg-white dark:bg-slate-900 text-indigo-600 dark:text-indigo-400 shadow-sm' : 'text-gray-500 dark:text-gray-400'}`}
        >
          Hệ thống nâng cao
        </button>
      </div>

      {section === 'basic' ? (
        <div className="space-y-6">
          <section className="rounded-2xl border border-gray-200 dark:border-slate-800 p-5">
            <div className="mb-4">
              <h3 className="text-sm font-bold text-gray-900 dark:text-white">Mô hình trả lời mặc định</h3>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Backend sẽ dùng chiến lược API/local fallback đã cấu hình trên server.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {AI_MODELS.map(model => (
                <button
                  key={model.id}
                  type="button"
                  onClick={() => updateDraft('model', model.id)}
                  className={`flex items-center justify-between gap-3 p-4 rounded-xl border text-left transition-all ${draft.model === model.id ? 'border-indigo-500 bg-indigo-50/60 dark:bg-indigo-500/10 ring-1 ring-indigo-500' : 'border-gray-200 dark:border-slate-700 hover:border-indigo-300 dark:hover:border-indigo-700'}`}
                >
                  <div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">{model.name}</p>
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{model.fullName}</p>
                  </div>
                  {draft.model === model.id && <Check className="w-4 h-4 text-indigo-600" />}
                </button>
              ))}
            </div>
          </section>

          <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <RangeSetting
              label="Temperature"
              value={draft.temperature}
              displayValue={draft.temperature.toFixed(2)}
              min={0}
              max={1}
              step={0.05}
              description="Độ sáng tạo của câu trả lời. Pháp luật nên dùng 0.1–0.3."
              onChange={value => updateDraft('temperature', value)}
            />
            <RangeSetting
              label="Max Tokens"
              value={draft.maxTokens}
              displayValue={String(draft.maxTokens)}
              min={100}
              max={4000}
              step={100}
              description="Giới hạn số token tối đa, không hoàn toàn tương đương số từ."
              onChange={value => updateDraft('maxTokens', value)}
            />
            <RangeSetting
              label="Số đoạn đưa cho AI (Top K)"
              value={draft.topK}
              displayValue={String(draft.topK)}
              min={1}
              max={20}
              step={1}
              description="Số điều khoản sau truy xuất/reranking được gửi cho mô hình."
              onChange={value => updateDraft('topK', value)}
            />
          </section>

          <div className="flex items-start gap-3 rounded-xl bg-blue-50 dark:bg-blue-500/10 border border-blue-100 dark:border-blue-500/20 p-4">
            <RefreshCw className="w-4 h-4 text-blue-600 dark:text-blue-400 mt-0.5 shrink-0" />
            <p className="text-xs leading-5 text-blue-700 dark:text-blue-300">
              Sau khi lưu, popup “Tham số” và bộ chọn mô hình ở màn hình chat sẽ tự đồng bộ. Cấu hình chỉ áp dụng cho trình duyệt hiện tại.
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-100 dark:border-amber-500/20 p-4 text-xs leading-5 text-amber-800 dark:text-amber-300">
            Các mục dưới đây thuộc cấu hình vận hành phía backend. Chúng được hiển thị để minh bạch kiến trúc và không thể thay đổi từ trình duyệt vì có thể yêu cầu khởi tạo lại model, index hoặc dịch vụ.
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {SYSTEM_FEATURES.map(feature => {
              const Icon = feature.icon;
              return (
                <div key={feature.title} className="rounded-2xl border border-gray-200 dark:border-slate-800 p-5 bg-white dark:bg-slate-900">
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-50 dark:bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center">
                      <Icon className="w-5 h-5" />
                    </div>
                    <span className="px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 text-[10px] font-bold uppercase tracking-wide">
                      {feature.status}
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-gray-900 dark:text-white">{feature.title}</h3>
                  <p className="text-xs leading-5 text-gray-500 dark:text-gray-400 mt-1.5">{feature.description}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

interface RangeSettingProps {
  label: string;
  value: number;
  displayValue: string;
  min: number;
  max: number;
  step: number;
  description: string;
  onChange: (value: number) => void;
}

function RangeSetting({ label, value, displayValue, min, max, step, description, onChange }: RangeSettingProps) {
  return (
    <div className="rounded-2xl border border-gray-200 dark:border-slate-800 p-5 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <label className="text-sm font-bold text-gray-900 dark:text-white">{label}</label>
        <span className="font-mono text-xs font-semibold text-indigo-600 dark:text-indigo-400 bg-indigo-50 dark:bg-indigo-500/10 px-2 py-1 rounded-lg">{displayValue}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={event => onChange(Number(event.target.value))}
        className="w-full h-2 bg-gray-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-indigo-600"
      />
      <p className="text-xs leading-5 text-gray-500 dark:text-gray-400">{description}</p>
    </div>
  );
}
