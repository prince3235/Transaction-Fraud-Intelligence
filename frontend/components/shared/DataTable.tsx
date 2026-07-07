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
import { OpaquePanel } from "./OpaquePanel";
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
      <OpaquePanel className={cn("overflow-hidden", className)}>
        <Table>
          <TableHeader>
            <TableRow>
              {columns.map((col, i) => (
                <TableHead key={i} className={col.className}>{col.header}</TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 5 }).map((_, i) => (
              <TableRow key={i}>
                {columns.map((col, j) => (
                  <TableCell key={j} className={col.className}>
                    <Skeleton className="h-4 w-full bg-mist/10" />
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </OpaquePanel>
    );
  }

  if (data.length === 0) {
    return (
      <OpaquePanel className={cn("p-8", className)}>
        <EmptyState
          title={emptyStateTitle}
          description={emptyStateDescription}
          action={emptyStateAction}
          icon={emptyStateIcon}
        />
      </OpaquePanel>
    );
  }

  return (
    <OpaquePanel className={cn("overflow-hidden", className)}>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="border-b border-mist/20 hover:bg-transparent">
              {columns.map((col, i) => (
                <TableHead key={i} className={cn("sticky top-0 bg-trench z-10", col.className)}>
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
                  "border-b border-mist/10",
                  onRowClick && "cursor-pointer hover:bg-mist/5 transition-colors duration-150"
                )}
              >
                {columns.map((col, j) => (
                  <TableCell key={j} className={col.className}>
                    {col.cell ? col.cell(item) : (col.accessorKey ? item[col.accessorKey] as React.ReactNode : null)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </OpaquePanel>
  );
}
