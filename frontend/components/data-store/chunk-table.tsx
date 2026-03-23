"use client";

import { useState, useMemo } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type ColumnFiltersState,
} from "@tanstack/react-table";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export interface Chunk {
  id: string;
  doc_id: string;
  chunk_type: string;
  page: number | null;
  section: string;
  content: string;
}

interface ChunkTableProps {
  data: Chunk[];
}

export function ChunkTable({ data }: ChunkTableProps) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState("");
  const [docFilter, setDocFilter] = useState("__all__");
  const [typeFilter, setTypeFilter] = useState("__all__");

  const uniqueDocs = useMemo(() => {
    const docs = new Set(data.map((c) => c.doc_id));
    return Array.from(docs).sort();
  }, [data]);

  const uniqueTypes = useMemo(() => {
    const types = new Set(data.map((c) => c.chunk_type));
    return Array.from(types).sort();
  }, [data]);

  const filteredData = useMemo(() => {
    let result = data;
    if (docFilter !== "__all__") {
      result = result.filter((c) => c.doc_id === docFilter);
    }
    if (typeFilter !== "__all__") {
      result = result.filter((c) => c.chunk_type === typeFilter);
    }
    return result;
  }, [data, docFilter, typeFilter]);

  const columns: ColumnDef<Chunk>[] = useMemo(
    () => [
      {
        accessorKey: "doc_id",
        header: "Document",
        cell: ({ row }) => (
          <span className="font-mono text-xs text-muted-foreground">
            {row.getValue<string>("doc_id")}
          </span>
        ),
        size: 160,
      },
      {
        accessorKey: "chunk_type",
        header: "Type",
        cell: ({ row }) => (
          <span className="inline-flex items-center rounded-md bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
            {row.getValue<string>("chunk_type")}
          </span>
        ),
        size: 100,
      },
      {
        accessorKey: "page",
        header: "Page",
        cell: ({ row }) => {
          const page = row.getValue<number | null>("page");
          return (
            <span className="text-xs text-muted-foreground">
              {page != null ? page : "\u2014"}
            </span>
          );
        },
        size: 60,
      },
      {
        accessorKey: "section",
        header: "Section",
        cell: ({ row }) => (
          <span className="text-xs">{row.getValue<string>("section") || "\u2014"}</span>
        ),
        size: 140,
      },
      {
        accessorKey: "content",
        header: "Content",
        cell: ({ row }) => {
          const content = row.getValue<string>("content");
          const truncated =
            content.length > 120 ? content.slice(0, 120) + "\u2026" : content;
          return (
            <span className="text-xs leading-relaxed text-foreground/80">
              {truncated}
            </span>
          );
        },
        enableSorting: false,
      },
    ],
    []
  );

  const table = useReactTable({
    data: filteredData,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    initialState: {
      pagination: {
        pageSize: 50,
      },
    },
  });

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Document
          </label>
          <select
            value={docFilter}
            onChange={(e) => setDocFilter(e.target.value)}
            className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground outline-none focus:border-ring focus:ring-3 focus:ring-ring/50 dark:bg-input/30"
          >
            <option value="__all__">All documents</option>
            {uniqueDocs.map((doc) => (
              <option key={doc} value={doc}>
                {doc}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Chunk Type
          </label>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="h-8 rounded-lg border border-input bg-transparent px-2.5 text-sm text-foreground outline-none focus:border-ring focus:ring-3 focus:ring-ring/50 dark:bg-input/30"
          >
            <option value="__all__">All types</option>
            {uniqueTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
            Search
          </label>
          <Input
            placeholder="Search content..."
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            className="w-[260px]"
          />
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-border bg-card">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    className={
                      header.column.getCanSort()
                        ? "cursor-pointer select-none"
                        : ""
                    }
                    onClick={header.column.getToggleSortingHandler()}
                  >
                    <span className="flex items-center gap-1">
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                      {header.column.getIsSorted() === "asc" && " \u2191"}
                      {header.column.getIsSorted() === "desc" && " \u2193"}
                    </span>
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.length > 0 ? (
              table.getRowModel().rows.map((row) => (
                <TableRow key={row.id}>
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center text-muted-foreground"
                >
                  No chunks match the current filters.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Showing{" "}
          {table.getState().pagination.pageIndex *
            table.getState().pagination.pageSize +
            1}
          {"\u2013"}
          {Math.min(
            (table.getState().pagination.pageIndex + 1) *
              table.getState().pagination.pageSize,
            table.getFilteredRowModel().rows.length
          )}{" "}
          of {table.getFilteredRowModel().rows.length} chunks
        </p>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
          >
            Previous
          </Button>
          <span className="text-xs text-muted-foreground">
            Page {table.getState().pagination.pageIndex + 1} of{" "}
            {table.getPageCount()}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  );
}
