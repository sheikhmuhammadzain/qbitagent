import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Database, RefreshCw, Info, Trash2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { api, type Database as DatabaseType, type DatabaseInfoResponse } from "@/lib/api";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

interface DatabaseSelectorProps {
  onDatabaseChange: () => void;
  setConnected: (connected: boolean) => void;
  setTools?: (tools: any[]) => void;
  setCurrentModel?: (model: string) => void;
}

export const DatabaseSelector = ({ onDatabaseChange, setConnected, setTools, setCurrentModel }: DatabaseSelectorProps) => {
  const [databases, setDatabases] = useState<DatabaseType[]>([]);
  const [selectedDatabase, setSelectedDatabase] = useState<string>("");
  const [databaseInfo, setDatabaseInfo] = useState<DatabaseInfoResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isInfoExpanded, setIsInfoExpanded] = useState(false);
  const { toast } = useToast();

  const loadDatabases = async () => {
    try {
      const result = await api.listDatabases();
      setDatabases(result.databases || []);
      
      // Check for active database from backend session (most reliable)
      const activeDatabaseId = (result as any).active_database_id;
      
      if (activeDatabaseId && result.databases.some(db => db.id === activeDatabaseId)) {
        console.log(`🔄 Restoring active database from session: ${activeDatabaseId}`);
        
        // Database is already connected on backend, sync UI state
        setSelectedDatabase(activeDatabaseId);
        setConnected(true);
        
        // Load database info (with error handling)
        try {
          await loadDatabaseInfo(activeDatabaseId);
          // Sync localStorage only if successful
          localStorage.setItem('selectedDatabaseId', activeDatabaseId);
        } catch (err) {
          console.error("Failed to restore database info:", err);
          // Clear session if database is not accessible
          setSelectedDatabase("");
          setConnected(false);
          localStorage.removeItem('selectedDatabaseId');
        }
        
        // Fetch tools
        try {
          const status = await api.status();
          if (status.tools && setTools) {
            setTools(status.tools);
          }
        } catch (err) {
          console.error("Failed to fetch tools:", err);
        }
      } else {
        // No active database in session, check localStorage as fallback
        const savedDatabaseId = localStorage.getItem('selectedDatabaseId');
        if (savedDatabaseId && result.databases.some(db => db.id === savedDatabaseId)) {
          console.log(`🔄 Attempting to restore database from localStorage: ${savedDatabaseId}`);
          // Try to reconnect
          await handleDatabaseSwitch(savedDatabaseId);
        }
      }
    } catch (error) {
      console.error("Failed to load databases:", error);
    }
  };

  const loadDatabaseInfo = async (dbId: string) => {
    try {
      const info = await api.getDatabaseInfo(dbId);
      setDatabaseInfo(info);
      setIsInfoExpanded(true);
    } catch (error) {
      console.error("Failed to load database info:", error);
      // Clear database info on error
      setDatabaseInfo(null);
      setIsInfoExpanded(false);
      
      // Show user-friendly error message
      toast({
        title: "Database not accessible",
        description: "This database may have been uploaded by a different user or no longer exists",
        variant: "destructive",
      });
    }
  };

  useEffect(() => {
    loadDatabases();
  }, []);

  const handleDatabaseSwitch = async (dbId: string) => {
    if (!dbId || dbId === selectedDatabase) return;

    setIsLoading(true);
    try {
      const result = await api.switchDatabase(dbId);
      setSelectedDatabase(dbId);
      setConnected(true);
      
      // Save to localStorage for persistence
      localStorage.setItem('selectedDatabaseId', dbId);
      
      // Fetch current status to get tools and model
      try {
        const status = await api.status();
        if (status.tools && setTools) {
          setTools(status.tools);
        }
        if (status.model && setCurrentModel) {
          setCurrentModel(status.model);
        }
      } catch (err) {
        console.error("Failed to fetch tools:", err);
      }

      toast({
        title: "Database switched",
        description: `Connected to ${result.database_name}`,
      });

      await loadDatabaseInfo(dbId);
      onDatabaseChange();
    } catch (error) {
      toast({
        title: "Failed to switch database",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = async () => {
    setIsLoading(true);
    await loadDatabases();
    setIsLoading(false);
  };

  const handleDeleteDatabase = async () => {
    if (!selectedDatabase) return;
    
    const dbName = databases.find(db => db.id === selectedDatabase)?.name || "this database";
    
    if (!confirm(`Are you sure you want to delete "${dbName}"? This action cannot be undone.`)) {
      return;
    }

    setIsLoading(true);
    try {
      await api.deleteDatabase(selectedDatabase);
      toast({
        title: "Database deleted",
        description: `${dbName} has been permanently deleted`,
      });
      
      // Clear selection and reload
      setSelectedDatabase("");
      setDatabaseInfo(null);
      setConnected(false);
      if (setTools) setTools([]);
      
      // Remove from localStorage
      localStorage.removeItem('selectedDatabaseId');
      
      await loadDatabases();
      onDatabaseChange();
    } catch (error) {
      toast({
        title: "Failed to delete database",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <Card className="p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-sm flex items-center gap-2">
          <Database className="h-4 w-4" />
          Database
        </h3>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 w-7 p-0"
          onClick={handleRefresh}
          disabled={isLoading}
        >
          <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      <Select value={selectedDatabase} onValueChange={handleDatabaseSwitch} disabled={isLoading}>
        <SelectTrigger>
          <SelectValue placeholder="Select database..." />
        </SelectTrigger>
        <SelectContent>
          {databases.length === 0 ? (
            <div className="p-2 text-sm text-muted-foreground text-center">
              No databases uploaded
            </div>
          ) : (
            databases.map((db) => (
              <SelectItem key={db.id} value={db.id}>
                {db.name} ({db.tables.length} {db.tables.length === 1 ? "table" : "tables"})
              </SelectItem>
            ))
          )}
        </SelectContent>
      </Select>

      {databaseInfo && selectedDatabase && (
        <Collapsible open={isInfoExpanded} onOpenChange={setIsInfoExpanded}>
          <CollapsibleTrigger asChild>
            <Button variant="outline" size="sm" className="w-full justify-start">
              <Info className="h-3.5 w-3.5 mr-2" />
              {isInfoExpanded ? "Hide" : "Show"} Database Info
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-3 space-y-2">
            <div className="text-xs space-y-1.5 p-3 bg-muted/50 rounded-md">
              <div className="flex justify-between gap-2">
                <span className="text-muted-foreground flex-shrink-0">Name:</span>
                <span className="font-medium truncate text-right" title={databaseInfo.name}>{databaseInfo.name}</span>
              </div>
              <div className="flex justify-between gap-2">
                <span className="text-muted-foreground flex-shrink-0">Size:</span>
                <span className="font-medium">{formatFileSize(databaseInfo.size_bytes)}</span>
              </div>
              <div className="flex justify-between gap-2">
                <span className="text-muted-foreground flex-shrink-0">Uploaded:</span>
                <span className="font-medium text-right text-[10px] leading-tight">{formatDate(databaseInfo.uploaded_at)}</span>
              </div>
            </div>

            <div className="space-y-1.5">
              <p className="text-xs font-medium">Tables:</p>
              {databaseInfo.tables.map((table, idx) => (
                <div key={idx} className="text-xs p-2 bg-muted/30 rounded border-l-2 border-primary">
                  <div className="font-medium">{table.name}</div>
                  <div className="text-muted-foreground">
                    {table.row_count} rows • {table.columns.length} columns
                  </div>
                </div>
              ))}
            </div>
            
            {/* Delete Database Button */}
            <Button
              variant="destructive"
              size="sm"
              className="w-full justify-start mt-2"
              onClick={handleDeleteDatabase}
              disabled={isLoading}
            >
              <Trash2 className="h-3.5 w-3.5 mr-2" />
              Delete Database
            </Button>
          </CollapsibleContent>
        </Collapsible>
      )}
    </Card>
  );
};
