import { apiPost } from './api';
import type { BugReport, BugReportCreate } from '@/types/api';

export async function createBugReport(data: BugReportCreate): Promise<BugReport> {
  return apiPost<BugReport>('/api/support/reports', data);
}
