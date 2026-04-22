'use client';

import { useState } from 'react';
import { Plus, Pencil, Trash2, ToggleLeft, ToggleRight, X, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  useAdminRules,
  createRule,
  updateRule,
  toggleRule,
  deleteRule,
  type RuleItem,
  type RuleCreate,
} from '@/lib/api/admin';

// ── Types ────────────────────────────────────────────────────────────────────

interface RulesTabTranslations {
  title: string;
  addRule: string;
  filters: {
    allLanguages: string;
    allCategories: string;
    allStatuses: string;
    active: string;
    inactive: string;
  };
  table: {
    name: string;
    language: string;
    category: string;
    severity: string;
    patternType: string;
    status: string;
    actions: string;
  };
  form: {
    addTitle: string;
    editTitle: string;
    language: string;
    name: string;
    description: string;
    category: string;
    severity: string;
    patternType: string;
    patternValue: string;
    exampleBad: string;
    exampleGood: string;
    save: string;
    cancel: string;
    saving: string;
  };
  deleteConfirm: string;
  noRules: string;
  severityLabels: { low: string; medium: string; high: string };
  patternTypeLabels: { regex: string; keyword: string; prompt: string; other: string };
}

interface Props {
  translations: RulesTabTranslations;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

const SEVERITY_COLORS = {
  low: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300',
  medium: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300',
  high: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
};

const PATTERN_TYPE_COLORS = {
  regex: 'bg-violet-100 text-violet-800 dark:bg-violet-900/30 dark:text-violet-300',
  keyword: 'bg-sky-100 text-sky-800 dark:bg-sky-900/30 dark:text-sky-300',
  prompt: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300',
  other: 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300',
};

const EMPTY_FORM: RuleCreate = {
  language: 'en',
  name: '',
  description: '',
  category: '',
  default_severity: 'medium',
  pattern_type: 'keyword',
  pattern_value: '',
  example_bad: '',
  example_good: '',
};

// ── Rule Form Modal ──────────────────────────────────────────────────────────

function RuleFormModal({
  rule,
  translations,
  onSave,
  onClose,
}: {
  rule: RuleItem | null;
  translations: RulesTabTranslations['form'];
  onSave: () => void;
  onClose: () => void;
}) {
  const [form, setForm] = useState<RuleCreate>(
    rule
      ? {
          language: rule.language as 'he' | 'en',
          name: rule.name,
          description: rule.description ?? '',
          category: rule.category,
          default_severity: rule.default_severity as 'low' | 'medium' | 'high',
          pattern_type: rule.pattern_type as 'regex' | 'keyword' | 'prompt' | 'other',
          pattern_value: rule.pattern_value,
          example_bad: rule.example_bad ?? '',
          example_good: rule.example_good ?? '',
        }
      : EMPTY_FORM,
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = <K extends keyof RuleCreate>(key: K, value: RuleCreate[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        ...form,
        description: form.description || undefined,
        example_bad: form.example_bad || undefined,
        example_good: form.example_good || undefined,
      };
      if (rule) {
        await updateRule(rule.rule_id, payload);
      } else {
        await createRule(payload);
      }
      onSave();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const inputCls =
    'w-full rounded-lg border border-slate-200 dark:border-slate-600 bg-white dark:bg-slate-800 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple/50';
  const labelCls = 'block text-xs font-medium text-slate-600 dark:text-slate-400 mb-1';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
          <h2 className="font-semibold text-slate-800 dark:text-white">
            {rule ? translations.editTitle : translations.addTitle}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
          {error && (
            <div className="flex items-center gap-2 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-3 py-2 text-sm text-red-700 dark:text-red-300">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {/* Language */}
            <div>
              <label className={labelCls}>{translations.language}</label>
              <select
                className={inputCls}
                value={form.language}
                onChange={(e) => set('language', e.target.value as 'he' | 'en')}
                required
              >
                <option value="en">English</option>
                <option value="he">עברית</option>
              </select>
            </div>

            {/* Severity */}
            <div>
              <label className={labelCls}>{translations.severity}</label>
              <select
                className={inputCls}
                value={form.default_severity}
                onChange={(e) => set('default_severity', e.target.value as 'low' | 'medium' | 'high')}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
              </select>
            </div>
          </div>

          {/* Name */}
          <div>
            <label className={labelCls}>{translations.name} *</label>
            <input
              className={inputCls}
              value={form.name}
              onChange={(e) => set('name', e.target.value)}
              required
              maxLength={200}
            />
          </div>

          {/* Category */}
          <div>
            <label className={labelCls}>{translations.category} *</label>
            <input
              className={inputCls}
              value={form.category}
              onChange={(e) => set('category', e.target.value)}
              required
              maxLength={100}
            />
          </div>

          {/* Description */}
          <div>
            <label className={labelCls}>{translations.description}</label>
            <textarea
              className={cn(inputCls, 'resize-y min-h-[60px]')}
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
              rows={2}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Pattern Type */}
            <div>
              <label className={labelCls}>{translations.patternType} *</label>
              <select
                className={inputCls}
                value={form.pattern_type}
                onChange={(e) =>
                  set('pattern_type', e.target.value as 'regex' | 'keyword' | 'prompt' | 'other')
                }
                required
              >
                <option value="keyword">Keyword</option>
                <option value="regex">Regex</option>
                <option value="prompt">Prompt</option>
                <option value="other">Other</option>
              </select>
            </div>

            {/* Pattern Value */}
            <div>
              <label className={labelCls}>{translations.patternValue} *</label>
              <input
                className={inputCls}
                value={form.pattern_value}
                onChange={(e) => set('pattern_value', e.target.value)}
                required
                dir={form.language === 'he' ? 'rtl' : 'ltr'}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Example bad */}
            <div>
              <label className={labelCls}>{translations.exampleBad}</label>
              <input
                className={inputCls}
                value={form.example_bad}
                onChange={(e) => set('example_bad', e.target.value)}
                dir={form.language === 'he' ? 'rtl' : 'ltr'}
              />
            </div>

            {/* Example good */}
            <div>
              <label className={labelCls}>{translations.exampleGood}</label>
              <input
                className={inputCls}
                value={form.example_good}
                onChange={(e) => set('example_good', e.target.value)}
                dir={form.language === 'he' ? 'rtl' : 'ltr'}
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg text-sm font-medium border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors"
            >
              {translations.cancel}
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 rounded-lg text-sm font-medium bg-pride-purple text-white hover:bg-pride-purple/90 disabled:opacity-60 transition-colors"
            >
              {saving ? translations.saving : translations.save}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Delete Confirmation ───────────────────────────────────────────────────────

function DeleteDialog({
  confirmText,
  onConfirm,
  onCancel,
}: {
  confirmText: string;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
      <div className="w-full max-w-sm bg-white dark:bg-slate-900 rounded-2xl shadow-xl p-6 space-y-4">
        <div className="flex items-center gap-3 text-red-600">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p className="text-sm font-medium">{confirmText}</p>
        </div>
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 rounded-lg text-sm font-medium border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className="px-4 py-2 rounded-lg text-sm font-medium bg-red-600 text-white hover:bg-red-700 transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function RulesTab({ translations }: Props) {
  const t = translations;

  const [page, setPage] = useState(1);
  const [filterLanguage, setFilterLanguage] = useState('');
  const [filterCategory, setFilterCategory] = useState('');
  const [filterEnabled, setFilterEnabled] = useState<boolean | undefined>(undefined);

  const [showForm, setShowForm] = useState(false);
  const [editingRule, setEditingRule] = useState<RuleItem | null>(null);
  const [deletingRuleId, setDeletingRuleId] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const { data, isLoading, refresh } = useAdminRules(
    page,
    20,
    filterLanguage || undefined,
    filterCategory || undefined,
    filterEnabled,
  );

  const handleToggle = async (rule: RuleItem) => {
    setTogglingId(rule.rule_id);
    try {
      await toggleRule(rule.rule_id, !rule.is_enabled);
      refresh();
    } finally {
      setTogglingId(null);
    }
  };

  const handleDelete = async () => {
    if (!deletingRuleId) return;
    await deleteRule(deletingRuleId);
    setDeletingRuleId(null);
    refresh();
  };

  const handleFormSave = () => {
    setShowForm(false);
    setEditingRule(null);
    refresh();
  };

  const badgeCls = 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium';

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-white">{t.title}</h2>
        <button
          onClick={() => { setEditingRule(null); setShowForm(true); }}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-pride-purple text-white text-sm font-medium hover:bg-pride-purple/90 transition-colors"
        >
          <Plus className="w-4 h-4" />
          {t.addRule}
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <select
          value={filterLanguage}
          onChange={(e) => { setFilterLanguage(e.target.value); setPage(1); }}
          className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple/50"
        >
          <option value="">{t.filters.allLanguages}</option>
          <option value="en">English</option>
          <option value="he">עברית</option>
        </select>

        <input
          type="text"
          placeholder={t.filters.allCategories}
          value={filterCategory}
          onChange={(e) => { setFilterCategory(e.target.value); setPage(1); }}
          className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple/50 min-w-[160px]"
        />

        <select
          value={filterEnabled === undefined ? '' : String(filterEnabled)}
          onChange={(e) => {
            setFilterEnabled(e.target.value === '' ? undefined : e.target.value === 'true');
            setPage(1);
          }}
          className="px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm focus:outline-none focus:ring-2 focus:ring-pride-purple/50"
        >
          <option value="">{t.filters.allStatuses}</option>
          <option value="true">{t.filters.active}</option>
          <option value="false">{t.filters.inactive}</option>
        </select>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-xl border border-slate-100 dark:border-slate-800 bg-white dark:bg-slate-900">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
              {[
                t.table.name,
                t.table.language,
                t.table.category,
                t.table.severity,
                t.table.patternType,
                t.table.status,
                t.table.actions,
              ].map((h) => (
                <th
                  key={h}
                  className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b border-slate-50 dark:border-slate-800/50 animate-pulse">
                  {Array.from({ length: 7 }).map((_, j) => (
                    <td key={j} className="px-4 py-3">
                      <div className="h-4 bg-slate-100 dark:bg-slate-800 rounded" />
                    </td>
                  ))}
                </tr>
              ))
            ) : !data?.rules.length ? (
              <tr>
                <td colSpan={7} className="px-4 py-12 text-center text-slate-400 text-sm">
                  {t.noRules}
                </td>
              </tr>
            ) : (
              data.rules.map((rule) => (
                <tr
                  key={rule.rule_id}
                  className={cn(
                    'border-b border-slate-50 dark:border-slate-800/50 hover:bg-slate-50/50 dark:hover:bg-slate-800/30 transition-colors',
                    !rule.is_enabled && 'opacity-50',
                  )}
                >
                  {/* Name + description */}
                  <td className="px-4 py-3 max-w-[220px]">
                    <div className="font-medium text-slate-800 dark:text-white truncate">{rule.name}</div>
                    {rule.description && (
                      <div className="text-xs text-slate-400 truncate mt-0.5">{rule.description}</div>
                    )}
                  </td>

                  {/* Language */}
                  <td className="px-4 py-3">
                    <span className={cn(badgeCls, 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300')}>
                      {rule.language.toUpperCase()}
                    </span>
                  </td>

                  {/* Category */}
                  <td className="px-4 py-3 max-w-[140px]">
                    <span className="text-slate-600 dark:text-slate-400 truncate block">{rule.category}</span>
                  </td>

                  {/* Severity */}
                  <td className="px-4 py-3">
                    <span className={cn(badgeCls, SEVERITY_COLORS[rule.default_severity])}>
                      {t.severityLabels[rule.default_severity]}
                    </span>
                  </td>

                  {/* Pattern type */}
                  <td className="px-4 py-3">
                    <span className={cn(badgeCls, PATTERN_TYPE_COLORS[rule.pattern_type])}>
                      {t.patternTypeLabels[rule.pattern_type]}
                    </span>
                  </td>

                  {/* Status toggle */}
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleToggle(rule)}
                      disabled={togglingId === rule.rule_id}
                      title={rule.is_enabled ? t.filters.active : t.filters.inactive}
                      className="transition-colors disabled:opacity-50"
                    >
                      {rule.is_enabled ? (
                        <ToggleRight className="w-6 h-6 text-emerald-500" />
                      ) : (
                        <ToggleLeft className="w-6 h-6 text-slate-400" />
                      )}
                    </button>
                  </td>

                  {/* Actions */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => { setEditingRule(rule); setShowForm(true); }}
                        className="p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-500 hover:text-pride-purple transition-colors"
                        title="Edit"
                      >
                        <Pencil className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => setDeletingRuleId(rule.rule_id)}
                        className="p-1.5 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/20 text-slate-500 hover:text-red-600 transition-colors"
                        title="Delete"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between text-sm text-slate-500">
          <span>
            {data.total} rules · page {data.page} of {data.total_pages}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
            >
              ←
            </button>
            <button
              onClick={() => setPage((p) => Math.min(data.total_pages, p + 1))}
              disabled={page === data.total_pages}
              className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 disabled:opacity-40 transition-colors"
            >
              →
            </button>
          </div>
        </div>
      )}

      {/* Modals */}
      {showForm && (
        <RuleFormModal
          rule={editingRule}
          translations={t.form}
          onSave={handleFormSave}
          onClose={() => { setShowForm(false); setEditingRule(null); }}
        />
      )}

      {deletingRuleId && (
        <DeleteDialog
          confirmText={t.deleteConfirm}
          onConfirm={handleDelete}
          onCancel={() => setDeletingRuleId(null)}
        />
      )}
    </div>
  );
}
