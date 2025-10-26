/**
 * Template-related TypeScript type definitions
 * Matches backend API response structures
 */

// Base Template Types (aligned with backend PDFTemplate model)
export interface Template {
  id: number;
  name: string;
  version: string;
  file_path: string;
  file_size_bytes: number;
  field_count: number;
  sepe_url: string | null;
  uploaded_by: number | null;
  created_at: string;
  updated_at: string | null;
}

// Enhanced Template Version with PDF metadata
export interface TemplateVersion {
  id: number;
  template_id: number;
  version_number: string;
  change_summary: string | null;
  is_current: boolean;
  created_at: string;
  // PDF Document Metadata
  title: string | null;
  author: string | null;
  subject: string | null;
  creation_date: string | null;
  modification_date: string | null;
  page_count: number;
}

// Template Field (AcroForm field data)
export interface TemplateField {
  id: number;
  version_id: number;
  field_id: string;
  field_type: FieldType;
  raw_type: string | null;
  page_number: number;
  field_page_order: number;
  near_text: string | null;
  value_options: string[] | null;
  position_data: PositionData | null;
  created_at: string;
}

// Position data for field coordinates
export interface PositionData {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

// Field types matching backend
export type FieldType =
  | 'text'
  | 'checkbox'
  | 'radiobutton'
  | 'select'
  | 'textarea'
  | 'button'
  | 'signature';

// Paginated Response Types
export interface TemplateListResponse {
  items: Template[];
  total: number;
  limit: number;
  offset: number;
}

export interface TemplateVersionListResponse {
  items: TemplateVersion[];
  total: number;
  limit: number;
  offset: number;
}

export interface TemplateFieldListResponse {
  items: TemplateField[];
  total: number;
  limit: number;
  offset: number;
  version_info: VersionInfo;
}

// Version metadata included in field responses
export interface VersionInfo {
  version_id: number;
  version_number: string;
  field_count: number;
}

// Filter and Sort Types
export interface TemplatesFilters {
  name?: string;
  version?: string;
  search?: string;
}

export interface VersionsFilters {
  limit?: number;
  offset?: number;
  sort_by?: 'created_at' | 'version_number' | 'page_count';
  sort_order?: 'asc' | 'desc';
}

export interface FieldsFilters {
  limit?: number;
  offset?: number;
  page_number?: number;
  search?: string;
}

export interface SortConfig {
  sort_by: string;
  sort_order: 'asc' | 'desc';
}

// Pagination State
export interface PaginationState {
  page: number;
  limit: number;
  total: number;
  offset: number;
}

// UI State Types
export interface TemplatesPageState {
  templates: Template[];
  loading: boolean;
  error: string | null;
  pagination: PaginationState;
  filters: TemplatesFilters;
  sort: SortConfig;
}

export interface ModalState {
  isOpen: boolean;
  templateId: number | null;
}

// Field Type Badge Colors (for UI display)
export const FIELD_TYPE_COLORS: Record<FieldType, string> = {
  text: 'blue',
  checkbox: 'green',
  radiobutton: 'purple',
  select: 'orange',
  textarea: 'blue',
  button: 'gray',
  signature: 'red',
};

// Field Type Display Labels
export const FIELD_TYPE_LABELS: Record<FieldType, string> = {
  text: 'Text',
  checkbox: 'Checkbox',
  radiobutton: 'Radio Button',
  select: 'Select',
  textarea: 'Text Area',
  button: 'Button',
  signature: 'Signature',
};

