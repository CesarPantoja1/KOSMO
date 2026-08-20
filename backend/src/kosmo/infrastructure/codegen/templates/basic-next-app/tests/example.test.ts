import { describe, expect, it } from "vitest";
import { cn } from "../src/lib/utils";

describe("basic template setup", () => {
  it("merges tailwind class names correctly", () => {
    // Arrange & Act
    const result = cn("px-2 py-1", "bg-blue-500", { "text-white": true, "hidden": false });

    // Assert
    expect(result).toBe("px-2 py-1 bg-blue-500 text-white");
  });
});
