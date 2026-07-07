import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "./EmptyState";
import { cn } from "@/lib/utils";

interface Column<T> {
  header: string;
  accessorKey?: keyof T;
  cell?: (item: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  isLoading?: boolean;
  onRowClick?: (item: T) => void;
  emptyStateTitle?: string;
  emptyStateDescription?: string;
  emptyStateAction?: React.ReactNode;
  emptyStateIcon?: React.ReactNode;
  className?: string;
}

export function DataTable<T extends { id: string }>({
  data,
  columns,
  isLoading,
  onRowClick,
  emptyStateTitle = "No data available",
  emptyStateDescription = "Records will appear here once they are created.",
  emptyStateAction,
  emptyStateIcon,
  className,
}: DataTableProps<T>) {
  if (isLoading) {
    return (
      <div className={cn("overflow-hidden w-full", className)}>
        <Table>
          <TableHeader>
            <TableRow className="border-b-2 border-ink/20">
              {columns.map((col, i) => (
                <TableHead key={i} className={col.className}>{col.header}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i} className="border-b border-ink/8">
                {columns.map((col, j) => (
                  <TableCell key={j} className={col.className}>
                    <Skeleton className="h-4 w-full bg-ink/10" />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className={cn("p-8 w-full", className)}>
        <EmptyState
          title={emptyStateTitle}
          description={emptyStateDescription}
          action={emptyStateAction}
          icon={emptyStateIcon}
        />
      </div>
    );
  }

  return (
    <div className={cn("overflow-hidden w-full", className)}>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-b-2 border-ink/20 hover:bg-transparent">
              {columns.map((col, i) => (
                <TableHead key={i} className={cn("sticky top-0 bg-paper z-10 text-ink/70 font-medium", col.className)}>
                  {col.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((item) => (
              <TableRow
                key={item.id}
                onClick={() => onRowClick?.(item)}
                className={cn(
                  "border-b border-ink/8",
                  onRowClick && "cursor-pointer hover:bg-ink/5 transition-colors duration-150"
                )}
              >
                {columns.map((col, j) => (
                  <TableCell key={j} className={cn("text-ink", col.className)}>
                    {col.cell ? col.cell(item) : (col.accessorKey ? item[col.accessorKey] as React.ReactNode : null)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
