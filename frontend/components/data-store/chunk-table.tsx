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
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";

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
        id: "row_num",
        header: "#",
        cell: ({ row }) => (
          <span className="text-xs font-mono text-muted-foreground/60">
            {row.index + 1}
          </span>
        ),
        size: 45,
        enableSorting: false,
      },
      {
        accessorKey: "doc_id",
        header: "Document",
        cell: ({ row }) => (
          <span className="font-mono text-xs text-orange-400">
            {row.getValue<string>("doc_id")}
          </span>
        ),
        size: 160,
      },
      {
        accessorKey: "chunk_type",
        header: "Type",
        cell: ({ row }) => (
          <span className="inline-flex items-center rounded-md bg-orange-500/20 px-2 py-0.5 text-xs font-medium text-orange-400">
            {row.getValue<string>("chunk_type")}
          </span>
        ),
        size: 90,
      },
      {
        accessorKey: "page",
        header: "Page",
        cell: ({ row }) => {
          const page = row.getValue<number | null>("page");
          return (
            <span className="text-xs text-zinc-400">{page != null ? page : "-"}</span>
          );
        },
        size: 55,
      },
      {
        accessorKey: "section",
        header: "Section",
        cell: ({ row }) => (
          <span className="text-xs text-zinc-300">{row.getValue<string>("section") || "-"}</span>
        ),
        size: 120,
      },
      {
        accessorKey: "content",
        header: "Content",
        cell: ({ row }) => {
          const content = row.getValue<string>("content");
          const truncated = content.length > 180 ? content.slice(0, 180) + "..." : content;
          return <span className="text-xs leading-relaxed text-zinc-200">{truncated}</span>;
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
        pageSize: 20,
      },
    },
  });

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap items-end gap-3 p-4 rounded-xl border border-orange-500/30 bg-zinc-900/50">
        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">
            Document
          </label>
          <select
            value={docFilter}
            onChange={(e) => setDocFilter(e.target.value)}
            className="h-9 min-w-[180px] rounded-lg border border-zinc-700 bg-zinc-800 px-3 text-sm text-zinc-200 outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500/50"
          >
            <option value="__all__" className="bg-zinc-800">All documents</option>
            {uniqueDocs.map((doc) => (
              <option key={doc} value={doc} className="bg-zinc-800">
                {doc}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">
            Chunk Type
          </label>
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="h-9 min-w-[140px] rounded-lg border border-zinc-700 bg-zinc-800 px-3 text-sm text-zinc-200 outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500/50"
          >
            <option value="__all__" className="bg-zinc-800">All types</option>
            {uniqueTypes.map((t) => (
              <option key={t} value={t} className="bg-zinc-800">
                {t}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">
            Search
          </label>
          <Input
            placeholder="Search content..."
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            className="h-9 w-[280px] rounded-lg border border-zinc-700 bg-zinc-800 px-3 text-sm text-zinc-200 placeholder:text-zinc-500 outline-none focus:border-orange-500 focus:ring-1 focus:ring-orange-500/50"
          />
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-zinc-700 bg-zinc-900 overflow-hidden">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              {table.getHeaderGroups().map((headerGroup) => (
                <TableRow key={headerGroup.id} className="border-zinc-700 hover:bg-zinc-800/50">
                  {headerGroup.headers.map((header) => (
                    <TableHead
                      key={header.id}
                      className={
                        header.column.getCanSort()
                          ? "cursor-pointer select-none hover:text-orange-400"
                          : ""
                      }
                      onClick={header.column.getToggleSortingHandler()}
                    >
                      <span className="flex items-center gap-1 text-zinc-500 text-xs uppercase tracking-wider font-medium">
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
                table.getRowModel().rows.map((row, idx) => (
                  <TableRow key={row.id} className="border-zinc-800/50 hover:bg-zinc-800/30">
                    {row.getVisibleCells().map((cell) => (
                      <TableCell key={cell.id} className="py-2.5">
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
                    className="h-24 text-center text-zinc-500"
                  >
                    No chunks match the current filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between p-3 rounded-xl border border-zinc-700 bg-zinc-900/50">
        <p className="text-xs text-zinc-500">
          Showing{" "}
          {table.getState().pagination.pageIndex *
            table.getState().pagination.pageSize +
            1}
          {" - "}
          {Math.min(
            (table.getState().pagination.pageIndex + 1) *
              table.getState().pagination.pageSize,
            table.getFilteredRowModel().rows.length
          )}{" "}
          of {table.getFilteredRowModel().rows.length} chunks
        </p>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => table.setPageIndex(0)}
            disabled={!table.getCanPreviousPage()}
            className="h-8 w-8 p-0 text-zinc-400 hover:text-orange-400 hover:bg-zinc-800"
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => table.previousPage()}
            disabled={!table.getCanPreviousPage()}
            className="h-8 px-2 text-zinc-400 hover:text-orange-400 hover:bg-zinc-800"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <span className="mx-3 text-xs text-zinc-500">
            <input
              type="number"
              value={table.getState().pagination.pageIndex + 1}
              onChange={(e) => {
                const page = parseInt(e.target.value);
                if (page >= 1 && page <= table.getPageCount()) {
                  table.setPageIndex(page - 1);
                }
              }}
              className="w-12 h-7 rounded border border-zinc-700 bg-zinc-800 px-1 text-center text-xs text-zinc-200 outline-none focus:border-orange-500"
            />{" "}
            / {table.getPageCount()}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => table.nextPage()}
            disabled={!table.getCanNextPage()}
            className="h-8 px-2 text-zinc-400 hover:text-orange-400 hover:bg-zinc-800"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => table.setPageIndex(table.getPageCount() - 1)}
            disabled={!table.getCanNextPage()}
            className="h-8 w-8 p-0 text-zinc-400 hover:text-orange-400 hover:bg-zinc-800"
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
