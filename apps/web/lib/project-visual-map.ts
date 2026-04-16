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

function repoRoot(): string {
  // RU: Web app живёт в apps/web, поэтому JSON карты читаем от корня репозитория, а не от cwd дев-сервера.
  return path.resolve(process.cwd(), '..', '..');
}

export async function getProjectVisualMap(): Promise<VisualMapPayload | null> {
  try {
    const filePath = path.join(repoRoot(), 'docs', 'ru', 'visuals', 'project-map.json');
    const payload = await fs.readFile(filePath, 'utf-8');
    return JSON.parse(payload) as VisualMapPayload;
  } catch {
    return null;
  }
}
