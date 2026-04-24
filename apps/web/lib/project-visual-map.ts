import {promises as fs} from 'node:fs';
import path from 'node:path';

type VisualMapPayload = {
  generated_at: string;
  validated_contour_en: string[];
  validated_contour_ru: string[];
  owned_capabilities_en: string[];
  owned_capabilities_ru: string[];
  danger_overlap_en: string[];
  danger_overlap_ru: string[];
  out_of_scope_en: string[];
  out_of_scope_ru: string[];
  skills: string[];
  automations: string[];
  active_context: Record<string, string>;
  recent_worklog: Array<Record<string, string>>;
};

type LegacyRuVisualMapPayload = {
  generated_at: string;
  validated_contour: string[];
  owned_capabilities: string[];
  danger_overlap: string[];
  out_of_scope: string[];
  автоматические_контуры: string[];
  навыки_проекта: string[];
};

function repoRoot(): string {
  // RU: Web app живёт в apps/web, поэтому JSON карты читаем от корня репозитория, а не от cwd дев-сервера.
  return path.resolve(process.cwd(), '..', '..');
}

function isVisualMapPayload(value: unknown): value is VisualMapPayload {
  return value !== null && typeof value === 'object' && 'active_context' in value;
}

function normalizeLegacyRuPayload(payload: LegacyRuVisualMapPayload): VisualMapPayload {
  return {
    generated_at: payload.generated_at,
    validated_contour_en: [],
    validated_contour_ru: payload.validated_contour ?? [],
    owned_capabilities_en: [],
    owned_capabilities_ru: payload.owned_capabilities ?? [],
    danger_overlap_en: [],
    danger_overlap_ru: payload.danger_overlap ?? [],
    out_of_scope_en: [],
    out_of_scope_ru: payload.out_of_scope ?? [],
    skills: payload.навыки_проекта ?? [],
    automations: payload.автоматические_контуры ?? [],
    // RU: Legacy ru-map не хранит active context/worklog, поэтому shell обязан переживать этот упрощённый формат без 500.
    active_context: {},
    recent_worklog: [],
  };
}

export async function getProjectVisualMap(): Promise<VisualMapPayload | null> {
  const root = repoRoot();
  const candidatePaths = [
    path.join(root, 'docs', 'visuals', 'project-map.json'),
    path.join(root, 'docs', 'ru', 'visuals', 'project-map.json'),
  ];

  try {
    for (const filePath of candidatePaths) {
      try {
        const raw = await fs.readFile(filePath, 'utf-8');
        const parsed = JSON.parse(raw) as VisualMapPayload | LegacyRuVisualMapPayload;
        if (isVisualMapPayload(parsed)) {
          return parsed;
        }
        return normalizeLegacyRuPayload(parsed);
      } catch {
        continue;
      }
    }
    return null;
  } catch {
    return null;
  }
}
