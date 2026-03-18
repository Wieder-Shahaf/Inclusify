'use client';

import { useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils';
import { FileText, Upload, FileType, Presentation, X } from 'lucide-react';

interface Translations {
  title: string;
  description: string;
  dragDrop: string;
  dropHere: string;
  chooseDifferent: string;
  analyzePaper: string;
  fileError: string;
  fileSizeError: string;
}

interface PaperUploadProps {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
  translations?: Translations;
}

const defaultTranslations: Translations = {
  title: 'Upload Your Paper',
  description: 'Drag and drop your document here, or click to browse',
  dragDrop: 'Drag and drop your document here, or click to browse',
  dropHere: 'Drop your file here',
  chooseDifferent: 'Choose Different File',
  analyzePaper: 'Analyze Paper',
  fileError: 'Please upload a PDF, DOCX, PPTX, or TXT file',
  fileSizeError: 'File size must be less than 10MB',
};

const acceptedExtensions = '.pdf,.docx,.pptx,.txt';

export default function PaperUpload({ onFileSelect, disabled, translations }: PaperUploadProps) {
  const labels = { ...defaultTranslations, ...translations };

  const [isDragging, setIsDragging] = useState(false);
  const [, setDragCounter] = useState(0);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback((file: File): boolean => {
    // Check by extension if MIME type detection fails
    const extension = file.name.toLowerCase().split('.').pop();
    const validExtensions = ['pdf', 'docx', 'pptx', 'txt'];

    if (!validExtensions.includes(extension || '')) {
      setError(labels.fileError);
      return false;
    }

    // Check file size (max 10MB)
    if (file.size > 10 * 1024 * 1024) {
      setError(labels.fileSizeError);
      return false;
    }

    setError(null);
    return true;
  }, [labels.fileError, labels.fileSizeError]);

  const handleFileSelect = useCallback((file: File) => {
    if (validateFile(file)) {
      setSelectedFile(file);
    }
  }, [validateFile]);

  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCounter(prev => prev + 1);
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragCounter(prev => {
      const newCount = prev - 1;
      if (newCount === 0) {
        setIsDragging(false);
      }
      return newCount;
    });
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    setDragCounter(0);

    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [handleFileSelect]);

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [handleFileSelect]);

  const handleConfirmUpload = useCallback(() => {
    if (selectedFile) {
      onFileSelect(selectedFile);
    }
  }, [selectedFile, onFileSelect]);

  const handleClearFile = useCallback(() => {
    setSelectedFile(null);
    setError(null);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  }, []);

  const getFileIcon = (file: File) => {
    const extension = file.name.toLowerCase().split('.').pop();
    switch (extension) {
      case 'pdf':
        return <FileText className="w-12 h-12 text-red-500" />;
      case 'docx':
        return <FileType className="w-12 h-12 text-blue-500" />;
      case 'pptx':
        return <Presentation className="w-12 h-12 text-orange-500" />;
      default:
        return <FileText className="w-12 h-12 text-slate-500" />;
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  return (
    <div className="w-full max-w-4xl mx-auto">
      <AnimatePresence mode="wait">
        {!selectedFile ? (
          <motion.div
            key="upload-zone"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            {/* Upload Zone */}
            <div
              className={cn(
                'relative rounded-2xl border-2 border-dashed transition-all duration-300 cursor-pointer overflow-hidden',
                'bg-gradient-to-br from-slate-50/80 to-white/60 dark:from-slate-900/80 dark:to-slate-800/60',
                isDragging
                  ? 'border-pride-purple scale-[1.02] shadow-xl shadow-pride-purple/20'
                  : 'border-slate-200 dark:border-slate-700 hover:border-pride-purple/50 hover:shadow-lg',
                disabled && 'opacity-50 cursor-not-allowed'
              )}
              onClick={() => !disabled && inputRef.current?.click()}
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if ((e.key === 'Enter' || e.key === ' ') && !disabled) {
                  inputRef.current?.click();
                }
              }}
              aria-label="Upload your paper for analysis"
            >
              <input
                ref={inputRef}
                type="file"
                accept={acceptedExtensions}
                onChange={handleInputChange}
                className="hidden"
                disabled={disabled}
              />

              {/* Animated background pattern */}
              <div className="absolute inset-0 opacity-30">
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_120%,rgba(123,97,255,0.3),transparent_50%)]" />
                <div className="absolute inset-0 bg-[radial-gradient(circle_at_0%_0%,rgba(255,83,161,0.2),transparent_50%)]" />
              </div>

              <div className="relative p-8 sm:p-12">
                <div className="flex flex-col items-center text-center">
                  {/* Upload Icon with Animation */}
                  <motion.div
                    className={cn(
                      'mb-5 p-5 rounded-2xl',
                      'bg-gradient-to-br from-pride-purple to-pride-pink',
                      'shadow-lg shadow-pride-purple/30'
                    )}
                    animate={isDragging ? { scale: [1, 1.1, 1], rotate: [0, 5, -5, 0] } : {}}
                    transition={{ duration: 0.5, repeat: isDragging ? Infinity : 0 }}
                  >
                    <Upload className="w-10 h-10 text-white" />
                  </motion.div>

                  <h3 className="text-xl sm:text-2xl font-semibold mb-2 text-slate-800 dark:text-white">
                    {labels.title}
                  </h3>
                  <p className="text-slate-500 dark:text-slate-400 mb-5 max-w-sm">
                    {labels.dragDrop}
                  </p>

                  {/* File Type Badges */}
                  <div className="flex flex-wrap justify-center gap-2">
                    {[
                      { ext: 'PDF', color: 'bg-red-100 text-red-600 dark:bg-red-900/30 dark:text-red-400' },
                      { ext: 'DOCX', color: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400' },
                      { ext: 'PPTX', color: 'bg-orange-100 text-orange-600 dark:bg-orange-900/30 dark:text-orange-400' },
                      { ext: 'TXT', color: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400' },
                    ].map(({ ext, color }) => (
                      <span
                        key={ext}
                        className={cn('px-3 py-1 rounded-full text-xs font-medium', color)}
                      >
                        {ext}
                      </span>
                    ))}
                  </div>

                  {/* Drag Indicator */}
                  <AnimatePresence>
                    {isDragging && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.9 }}
                        className="absolute inset-0 flex items-center justify-center bg-pride-purple/10 backdrop-blur-sm rounded-2xl"
                      >
                        <div className="text-center">
                          <motion.div
                            animate={{ y: [0, -10, 0] }}
                            transition={{ duration: 0.5, repeat: Infinity }}
                          >
                            <Upload className="w-16 h-16 text-pride-purple mx-auto mb-4" />
                          </motion.div>
                          <p className="text-lg font-semibold text-pride-purple">
                            {labels.dropHere}
                          </p>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </div>

            {/* Error Message */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="mt-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-600 dark:text-red-400 text-center"
                >
                  {error}
                </motion.div>
              )}
            </AnimatePresence>

          </motion.div>
        ) : (
          /* Selected File Preview */
          <motion.div
            key="file-preview"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="p-6 rounded-2xl glass border"
          >
            <div className="flex items-start gap-4">
              <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-800">
                {getFileIcon(selectedFile)}
              </div>
              <div className="flex-1 min-w-0">
                <h4 className="font-semibold text-slate-800 dark:text-white truncate">
                  {selectedFile.name}
                </h4>
                <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                  {formatFileSize(selectedFile.size)}
                </p>
              </div>
              <button
                onClick={handleClearFile}
                className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                aria-label="Remove file"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={handleClearFile}
                className="flex-1 py-3 px-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors font-medium"
              >
                {labels.chooseDifferent}
              </button>
              <motion.button
                onClick={handleConfirmUpload}
                className="flex-1 btn-primary py-3 px-4"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {labels.analyzePaper}
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
