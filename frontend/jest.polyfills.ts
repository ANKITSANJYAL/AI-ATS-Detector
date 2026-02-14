/**
 * Jest polyfills for browser APIs unavailable in jsdom.
 */

// jsdom doesn't implement URL.createObjectURL / revokeObjectURL
if (typeof URL.createObjectURL === "undefined") {
  URL.createObjectURL = () => "blob:mock-url";
}
if (typeof URL.revokeObjectURL === "undefined") {
  URL.revokeObjectURL = () => {};
}
