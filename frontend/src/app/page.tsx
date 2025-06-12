"use client";

import { useEffect, useState, useCallback } from "react";
import api, { ApiPaperBase } from "@/lib/api";
import PaperCard from "@/components/paper-card";
import { useAuth } from "@/context/auth-context";
import FilterPanel, { Filters } from "@/components/filter-panel";
import PaginationControls from "@/components/pagination-controls";
import PaperCardSkeleton from "@/components/paper-card-skeleton";
import { useDebounce } from "@/hooks/use-debounce";
import { Badge } from "@/components/ui/badge";
import { X } from "lucide-react";

export default function HomePage() {
  const [papers, setPapers] = useState<ApiPaperBase[]>([]);
  const [bookmarkedIds, setBookmarkedIds] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);

  // State for pagination
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  // State for filters
  const [filters, setFilters] = useState<Filters>({
    search: "",
    has_code: false,
  });

  const { isAuthenticated } = useAuth();

  const debouncedSearchTerm = useDebounce(filters.search, 500);

  const fetchPapers = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams({
        page: String(currentPage),
        per_page: "12",
      });

      if (debouncedSearchTerm) params.append("search", debouncedSearchTerm);
      if (filters.has_code) params.append("has_code", "true");

      const response = await api.get("/papers", { params });
      setPapers(response.data.items);
      setTotalPages(response.data.total_pages);
    } catch (error) {
      console.error("Failed to fetch papers:", error);
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, filters.has_code, debouncedSearchTerm]);

  useEffect(() => {
    fetchPapers();
  }, [fetchPapers]);

  const fetchBookmarks = useCallback(async () => {
    if (isAuthenticated) {
      const response = await api.get("/me/bookmarks");
      const ids = new Set<string>(response.data.map((p: ApiPaperBase) => p.id));
      setBookmarkedIds(ids);
    } else {
      setBookmarkedIds(new Set());
    }
  }, [isAuthenticated]);

  useEffect(() => {
    fetchBookmarks();
  }, [fetchBookmarks]);

  const handleBookmarkToggle = (paperId: string) => {
    const newBookmarkedIds = new Set(bookmarkedIds);
    if (newBookmarkedIds.has(paperId)) {
      newBookmarkedIds.delete(paperId);
    } else {
      newBookmarkedIds.add(paperId);
    }
    setBookmarkedIds(newBookmarkedIds);
  };

  const handleFilterChange = (newFilters: Partial<Filters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }));
  };

  const handleApplyFilters = () => {
    setCurrentPage(1); // Reset to first page on new filter application
    fetchPapers();
  };

  const handlePageChange = (page: number) => {
    setCurrentPage(page);
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
      {/* Filter Panel on the side */}
      <aside className="lg:col-span-1">
        <FilterPanel
          filters={filters}
          onFilterChange={handleFilterChange}
          onApplyFilters={handleApplyFilters}
        />
      </aside>

      {/* Main content */}
      <main className="lg:col-span-3">
        <h1 className="text-3xl font-bold mb-6">Papers</h1>

        {(filters.search || filters.has_code) && (
          <div className="flex flex-wrap items-center gap-2 mb-4 min-h-[2rem]">
            {filters.search && (
              <Badge variant="secondary" className="flex items-center gap-1">
                Search: &quot;{filters.search}&quot;
              </Badge>
            )}
            {filters.has_code && (
              <Badge variant="secondary" className="flex items-center gap-1">
                Has Code
                <button onClick={() => handleFilterChange({ has_code: false })}>
                  <X className="h-3 w-3" />
                </button>
              </Badge>
            )}
          </div>
        )}

        {isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            {Array.from({ length: 6 }).map((_, index) => (
              <PaperCardSkeleton key={index} />
            ))}
          </div>
        ) : papers.length > 0 ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {papers.map((paper) => (
                <PaperCard
                  key={paper.id}
                  paper={paper}
                  isBookmarked={bookmarkedIds.has(paper.id)}
                  onBookmarkToggle={handleBookmarkToggle}
                />
              ))}
            </div>
            <PaginationControls
              currentPage={currentPage}
              totalPages={totalPages}
              onPageChange={handlePageChange}
            />
          </>
        ) : (
          <p>No papers found matching your criteria.</p>
        )}
      </main>
    </div>
  );
}
