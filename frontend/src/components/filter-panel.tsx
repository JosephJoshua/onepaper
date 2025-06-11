"use client";

import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Button } from "./ui/button";

export interface Filters {
  search: string;
  has_code: boolean;
}

interface FilterPanelProps {
  filters: Filters;
  onFilterChange: (newFilters: Partial<Filters>) => void;
  onApplyFilters: () => void;
}

export default function FilterPanel({
  filters,
  onFilterChange,
  onApplyFilters,
}: FilterPanelProps) {
  return (
    <div className="p-4 border rounded-lg space-y-4">
      <h3 className="text-lg font-semibold">Filters</h3>

      {/* Search Input */}
      <div className="space-y-2">
        <Label htmlFor="search">Search</Label>
        <Input
          id="search"
          placeholder="Search title or abstract..."
          value={filters.search}
          onChange={(e) => onFilterChange({ search: e.target.value })}
        />
      </div>

      {/* Switches */}
      <div className="flex items-center justify-between">
        <Label htmlFor="has-code">Has Code</Label>
        <Switch
          id="has-code"
          checked={filters.has_code}
          onCheckedChange={(checked) => onFilterChange({ has_code: checked })}
        />
      </div>

      <Button onClick={onApplyFilters} className="w-full">
        Apply Filters
      </Button>
    </div>
  );
}
