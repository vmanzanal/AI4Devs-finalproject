/**
 * TemplatesPage Component
 *
 * Main page for displaying and managing PDF templates with:
 * - Templates table with sorting and pagination
 * - Search and filter functionality
 * - Download template PDFs
 * - View version history in modal
 * - View form fields in modal
 * - Loading and error states
 * - Responsive design
 *
 * Integrates:
 * - useTemplates hook for main data
 * - useTemplateVersions hook for version history modal
 * - useTemplateFields hook for fields modal
 * - All table and modal components
 *
 * @author AI4Devs
 * @date 2025-10-25
 */

import React, { useState } from 'react';
import TableFilters from '../../components/templates/TableFilters';
import TablePagination from '../../components/templates/TablePagination';
import TemplateFieldsModal from '../../components/templates/TemplateFieldsModal';
import TemplatesTable from '../../components/templates/TemplatesTable';
import VersionHistoryModal from '../../components/templates/VersionHistoryModal';
import { useTemplateFields } from '../../hooks/useTemplateFields';
import { useTemplates } from '../../hooks/useTemplates';
import { useTemplateVersions } from '../../hooks/useTemplateVersions';
import { templatesService } from '../../services/templates.service';
import { downloadBlob } from '../../utils/file-download';

/**
 * TemplatesPage - Main page for template management
 *
 * @example
 * ```tsx
 * // In router configuration
 * <Route path="/templates" element={<TemplatesPage />} />
 * ```
 */
const TemplatesPage: React.FC = () => {
  // Main templates data
  const {
    templates,
    total,
    isLoading,
    error,
    currentPage,
    totalPages,
    setPage,
    setPageSize,
    pagination,
    sort,
    handleSort,
    search,
    setSearch,
  } = useTemplates();

  // Version history modal data
  const {
    versions,
    isLoading: versionsLoading,
    error: versionsError,
    templateId: versionsTemplateId,
    currentPage: versionsCurrentPage,
    totalPages: versionsTotalPages,
    setPage: setVersionsPage,
    fetchVersions,
    clearVersions,
  } = useTemplateVersions();

  // Fields modal data
  const {
    fields,
    isLoading: fieldsLoading,
    error: fieldsError,
    templateId: fieldsTemplateId,
    versionInfo,
    currentPage: fieldsCurrentPage,
    totalPages: fieldsTotalPages,
    setPage: setFieldsPage,
    search: fieldsSearch,
    setSearch: setFieldsSearch,
    pageNumber: fieldsPageNumber,
    setPageNumber: setFieldsPageNumber,
    clearPageNumber: clearFieldsPageNumber,
    fetchCurrentVersionFields,
    clearFields,
  } = useTemplateFields();

  // Local state for modals
  const [selectedTemplateName, setSelectedTemplateName] = useState('');
  const [downloadError, setDownloadError] = useState<string | null>(null);

  /**
   * Handle template download
   */
  const handleDownload = async (templateId: number) => {
    setDownloadError(null);
    try {
      const { blob, filename } = await templatesService.downloadTemplate(
        templateId
      );
      downloadBlob(blob, filename);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to download template';
      setDownloadError(errorMessage);
      // Auto-clear error after 5 seconds
      setTimeout(() => setDownloadError(null), 5000);
    }
  };

  /**
   * Handle opening version history modal
   */
  const handleViewVersions = (templateId: number) => {
    const template = templates.find((t) => t.id === templateId);
    if (template) {
      setSelectedTemplateName(template.name);
      fetchVersions(templateId);
    }
  };

  /**
   * Handle closing version history modal
   */
  const handleCloseVersionsModal = () => {
    clearVersions();
    setSelectedTemplateName('');
  };

  /**
   * Handle opening fields modal
   */
  const handleViewFields = (templateId: number) => {
    const template = templates.find((t) => t.id === templateId);
    if (template) {
      setSelectedTemplateName(template.name);
      fetchCurrentVersionFields(templateId);
    }
  };

  /**
   * Handle closing fields modal
   */
  const handleCloseFieldsModal = () => {
    clearFields();
    setSelectedTemplateName('');
  };

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          Templates
        </h1>
      </div>

      {/* Download error toast */}
      {downloadError && (
        <div
          className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4"
          role="alert"
        >
          <p className="text-red-800 dark:text-red-200">{downloadError}</p>
        </div>
      )}

      {/* Main error display */}
      {error && !isLoading && (
        <div
          className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6"
          role="alert"
        >
          <h3 className="text-lg font-semibold text-red-800 dark:text-red-200 mb-2">
            Error Loading Templates
          </h3>
          <p className="text-red-700 dark:text-red-300">{error}</p>
        </div>
      )}

      {/* Content container */}
      {!error && (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm">
          {/* Filters */}
          {!isLoading && templates && templates.length > 0 && (
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <TableFilters search={search} onSearchChange={setSearch} />
            </div>
          )}

          {/* Table */}
          <div className="overflow-x-auto">
            <TemplatesTable
              templates={templates || []}
              isLoading={isLoading}
              sortBy={sort.sort_by}
              sortOrder={sort.sort_order}
              onSort={handleSort}
              onDownload={handleDownload}
              onViewVersions={handleViewVersions}
              onViewFields={handleViewFields}
            />
          </div>

          {/* Pagination */}
          {!isLoading && !error && templates && templates.length > 0 && (
            <TablePagination
              currentPage={currentPage}
              totalPages={totalPages}
              pageSize={pagination.limit}
              totalItems={total}
              onPageChange={setPage}
              onPageSizeChange={setPageSize}
            />
          )}
        </div>
      )}

      {/* Version History Modal */}
      <VersionHistoryModal
        isOpen={versionsTemplateId !== null}
        onClose={handleCloseVersionsModal}
        templateName={selectedTemplateName}
        versions={versions}
        isLoading={versionsLoading}
        error={versionsError}
        currentPage={versionsCurrentPage}
        totalPages={versionsTotalPages}
        onPageChange={setVersionsPage}
      />

      {/* Template Fields Modal */}
      <TemplateFieldsModal
        isOpen={fieldsTemplateId !== null}
        onClose={handleCloseFieldsModal}
        templateName={selectedTemplateName}
        fields={fields}
        versionInfo={versionInfo}
        isLoading={fieldsLoading}
        error={fieldsError}
        currentPage={fieldsCurrentPage}
        totalPages={fieldsTotalPages}
        search={fieldsSearch}
        pageNumber={fieldsPageNumber}
        onPageChange={setFieldsPage}
        onSearchChange={setFieldsSearch}
        onPageNumberFilter={setFieldsPageNumber}
        onClearPageFilter={clearFieldsPageNumber}
      />
    </div>
  );
};

export default TemplatesPage;
