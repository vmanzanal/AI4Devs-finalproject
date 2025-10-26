/**
 * Templates Service - API integration for template management
 *
 * Handles communication with the backend templates endpoints for:
 * - Fetching templates list with pagination, sorting, and filtering
 * - Downloading template PDFs
 * - Fetching template versions with metadata
 * - Fetching template AcroForm fields
 *
 * Features:
 * - Authentication token management (via apiService)
 * - Error handling and response parsing
 * - TypeScript type safety for requests and responses
 * - Support for pagination, sorting, filtering, and search
 *
 * @author AI4Devs
 * @date 2025-10-25
 */

import type {
    FieldsFilters,
    TemplateFieldListResponse,
    TemplateListResponse,
    TemplatesFilters,
    TemplateVersionListResponse,
    VersionsFilters,
} from '../types/templates.types';
import { apiService } from './apiService';

/**
 * Templates Service class for template management API operations
 */
class TemplatesService {
  /**
   * Fetch all templates with pagination, sorting, and filtering
   *
   * @param filters - Optional filters for pagination, sorting, and search
   * @returns Promise resolving to paginated list of templates
   * @throws Error if API request fails
   *
   * @example
   * ```typescript
   * // Fetch first page with default settings
   * const templates = await templatesService.getTemplates();
   *
   * // Fetch with custom pagination and sorting
   * const templates = await templatesService.getTemplates({
   *   limit: 50,
   *   offset: 100,
   *   sort_by: 'name',
   *   sort_order: 'asc',
   *   search: 'SEPE'
   * });
   * ```
   */
  async getTemplates(
    filters?: TemplatesFilters
  ): Promise<TemplateListResponse> {
    const params = {
      limit: filters?.limit ?? 20,
      offset: filters?.offset ?? 0,
      sort_by: filters?.sort_by ?? 'updated_at',
      sort_order: filters?.sort_order ?? 'desc',
      ...(filters?.search && { search: filters.search }),
    };

    return apiService.get<TemplateListResponse>('/templates/', params);
  }

  /**
   * Download a template PDF file
   *
   * Downloads the PDF file of a template's current version.
   * Returns a Blob object and the suggested filename from the server.
   *
   * @param templateId - The ID of the template to download
   * @returns Promise resolving to Blob and filename
   * @throws Error if download fails or template not found
   *
   * @example
   * ```typescript
   * const { blob, filename } = await templatesService.downloadTemplate(1);
   * // Use with file-download utilities to trigger browser download
   * downloadBlob(blob, filename);
   * ```
   */
  async downloadTemplate(
    templateId: number
  ): Promise<{ blob: Blob; filename: string }> {
    const token = localStorage.getItem('access_token');
    const baseURL =
      import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

    const response = await fetch(
      `${baseURL}/templates/${templateId}/download`,
      {
        method: 'GET',
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    if (!response.ok) {
      throw new Error(
        `Failed to download template: ${response.status} ${response.statusText}`
      );
    }

    const blob = await response.blob();

    // Extract filename from Content-Disposition header
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = `template_${templateId}.pdf`;

    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(
        /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/
      );
      if (filenameMatch && filenameMatch[1]) {
        filename = filenameMatch[1].replace(/['"]/g, '');
      }
    }

    return { blob, filename };
  }

  /**
   * Fetch all versions of a specific template
   *
   * Returns version history with full PDF metadata including title, author,
   * subject, page count, and document dates.
   *
   * @param templateId - The ID of the template
   * @param filters - Optional filters for pagination and sorting
   * @returns Promise resolving to paginated list of template versions
   * @throws Error if template not found or API request fails
   *
   * @example
   * ```typescript
   * // Fetch versions with default settings
   * const versions = await templatesService.getTemplateVersions(1);
   *
   * // Fetch with custom sorting
   * const versions = await templatesService.getTemplateVersions(1, {
   *   sort_by: 'version_number',
   *   sort_order: 'asc'
   * });
   * ```
   */
  async getTemplateVersions(
    templateId: number,
    filters?: VersionsFilters
  ): Promise<TemplateVersionListResponse> {
    const params = {
      limit: filters?.limit ?? 20,
      offset: filters?.offset ?? 0,
      sort_by: filters?.sort_by ?? 'created_at',
      sort_order: filters?.sort_order ?? 'desc',
    };

    return apiService.get<TemplateVersionListResponse>(
      `/templates/${templateId}/versions`,
      params
    );
  }

  /**
   * Fetch all AcroForm fields from the current version of a template
   *
   * Returns fields with pagination, search, and filtering by page number.
   * Fields are ordered by page_number, then field_page_order.
   *
   * @param templateId - The ID of the template
   * @param filters - Optional filters for pagination, search, and page filter
   * @returns Promise resolving to paginated list of template fields
   * @throws Error if template not found or no current version exists
   *
   * @example
   * ```typescript
   * // Fetch all fields from current version
   * const fields = await templatesService.getCurrentVersionFields(1);
   *
   * // Search for specific fields on page 2
   * const fields = await templatesService.getCurrentVersionFields(1, {
   *   page_number: 2,
   *   search: 'email',
   *   limit: 50
   * });
   * ```
   */
  async getCurrentVersionFields(
    templateId: number,
    filters?: FieldsFilters
  ): Promise<TemplateFieldListResponse> {
    const params = {
      limit: filters?.limit ?? 20,
      offset: filters?.offset ?? 0,
      ...(filters?.page_number && { page_number: filters.page_number }),
      ...(filters?.search && { search: filters.search }),
    };

    return apiService.get<TemplateFieldListResponse>(
      `/templates/${templateId}/fields/current`,
      params
    );
  }

  /**
   * Fetch all AcroForm fields from a specific version of a template
   *
   * Returns fields with pagination, search, and filtering by page number.
   * Useful for historical analysis and version comparison.
   *
   * @param templateId - The ID of the template
   * @param versionId - The ID of the specific version
   * @param filters - Optional filters for pagination, search, and page filter
   * @returns Promise resolving to paginated list of template fields
   * @throws Error if template or version not found
   *
   * @example
   * ```typescript
   * // Fetch all fields from version 5
   * const fields = await templatesService.getVersionFields(1, 5);
   *
   * // Search in specific version
   * const fields = await templatesService.getVersionFields(1, 5, {
   *   search: 'checkbox'
   * });
   * ```
   */
  async getVersionFields(
    templateId: number,
    versionId: number,
    filters?: FieldsFilters
  ): Promise<TemplateFieldListResponse> {
    const params = {
      limit: filters?.limit ?? 20,
      offset: filters?.offset ?? 0,
      ...(filters?.page_number && { page_number: filters.page_number }),
      ...(filters?.search && { search: filters.search }),
    };

    return apiService.get<TemplateFieldListResponse>(
      `/templates/${templateId}/versions/${versionId}/fields`,
      params
    );
  }
}

// Export singleton instance
export const templatesService = new TemplatesService();

// Export class for testing purposes
export { TemplatesService };

