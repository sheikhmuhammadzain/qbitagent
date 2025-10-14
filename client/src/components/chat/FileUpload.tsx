import { useState, useRef, DragEvent } from "react";
import { Button } from "@/components/ui/button";
import { Upload } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { api, type UploadResponse } from "@/lib/api";
import { Progress } from "@/components/ui/progress";

interface FileUploadProps {
  onUploadSuccess: (result: UploadResponse) => void;
}

export const FileUpload = ({ onUploadSuccess }: FileUploadProps) => {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  const validateFile = (file: File): boolean => {
    const validTypes = [
      "text/csv",
      "application/vnd.ms-excel",
      "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ];
    const validExtensions = /\.(csv|xlsx|xls)$/i;

    if (!validTypes.includes(file.type) && !validExtensions.test(file.name)) {
      toast({
        title: "Invalid file type",
        description: "Please upload a CSV or Excel file (.csv, .xlsx, .xls)",
        variant: "destructive",
      });
      return false;
    }

    const maxSize = 100 * 1024 * 1024; // 100MB
    if (file.size > maxSize) {
      toast({
        title: "File too large",
        description: "Maximum file size is 100MB",
        variant: "destructive",
      });
      return false;
    }

    return true;
  };

  const handleFileUpload = async (file: File) => {
    if (!validateFile(file)) return;

    setIsUploading(true);
    setUploadProgress(0);

    // Simulate progress for better UX
    const progressInterval = setInterval(() => {
      setUploadProgress((prev) => Math.min(prev + 10, 90));
    }, 200);

    try {
      const result = await api.uploadFile(file);
      
      clearInterval(progressInterval);
      setUploadProgress(100);

      const rowCount = result.row_count || result.total_rows || 0;
      toast({
        title: "Upload successful",
        description: `Database created with ${rowCount} rows`,
      });

      onUploadSuccess(result);
    } catch (error) {
      clearInterval(progressInterval);
      toast({
        title: "Upload failed",
        description: error instanceof Error ? error.message : "Failed to upload file",
        variant: "destructive",
      });
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      await handleFileUpload(files[0]);
    }
  };

  const handleFileSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      await handleFileUpload(files[0]);
    }
  };

  const openFilePicker = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="space-y-3">
      <div
        className={`
          border-2 border-dashed rounded-lg p-6 text-center cursor-pointer
          transition-all duration-200
          ${isDragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"}
          ${isUploading ? "opacity-50 cursor-not-allowed" : ""}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={!isUploading ? openFilePicker : undefined}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          onChange={handleFileSelect}
          className="hidden"
          disabled={isUploading}
        />

        <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
        <p className="text-sm font-medium mb-1">
          {isDragging ? "Drop file here" : "Drop CSV/Excel here"}
        </p>
        <p className="text-xs text-muted-foreground mb-3">
          or click to browse
        </p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={isUploading}
          onClick={(e) => {
            e.stopPropagation();
            openFilePicker();
          }}
        >
          Browse Files
        </Button>
        <p className="text-xs text-muted-foreground mt-3">
          Max 100MB • CSV, XLSX, XLS
        </p>
      </div>

      {isUploading && (
        <div className="space-y-2">
          <Progress value={uploadProgress} className="h-1" />
          <p className="text-xs text-center text-muted-foreground">
            Uploading and converting... {uploadProgress}%
          </p>
        </div>
      )}
    </div>
  );
};
