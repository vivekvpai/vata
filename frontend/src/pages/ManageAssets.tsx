import { useState, useEffect } from "react";
import {
  Database,
  X,
  FileText,
  Layout,
  Hash,
  Sparkles,
  Loader2,
  RefreshCw,
  ThumbsUp,
  ThumbsDown,
  ChevronRight,
  Trash2,
  Clock,
  Calendar,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useToast } from "../contexts/ToastContext";
import { CategoryService } from "../services/categoryService";
import { AssetService } from "../services/assetService";
import { AIService } from "../services/aiService";
import ConfirmModal from "../components/ConfirmModal";

const ManageAssets = () => {
  const { showToast } = useToast();

  // Helper to format category names (stripping timestamp)
  const formatCategoryName = (id: string | null) => {
    if (!id) return "";
    const parts = id.split("_");
    return parts.length > 1 ? parts.slice(0, -1).join("_") : id;
  };

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return "";
    try {
      const date = new Date(dateString);
      return new Intl.DateTimeFormat("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
      }).format(date);
    } catch (e) {
      return dateString;
    }
  };

  // State
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategoryId, setSelectedCategoryId] = useState<string | null>(
    null,
  );
  const [fullCategoryContent, setFullCategoryContent] = useState<any>(null);
  const [selectedAssetId, setSelectedAssetId] = useState<string | null>(null);

  const [isDataLoading, setIsDataLoading] = useState(false);
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // Form State (for the selected asset)
  const [formData, setFormData] = useState({
    main_content: "",
    summary: "",
  });
  const [tags, setTags] = useState<string[]>([]);
  const [currentTag, setCurrentTag] = useState("");

  const [suggestions, setSuggestions] = useState<{
    summary: string | null;
    tags: string[] | null;
  }>({
    summary: null,
    tags: null,
  });

  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  const clearForm = () => {
    if (!selectedAssetId || !fullCategoryContent) return;
    const asset = fullCategoryContent.data[selectedAssetId];
    if (asset) {
      setFormData({
        main_content: asset.main_content || "",
        summary: asset.summary || "",
      });
      setTags(asset.tags || []);
      setSuggestions({ summary: null, tags: null });
      showToast("info", "Form Reset", "The editing fields have been restored.");
    }
  };

  const acceptAllSuggestions = () => {
    if (suggestions.summary)
      setFormData((prev) => ({ ...prev, summary: suggestions.summary! }));
    if (suggestions.tags) setTags(suggestions.tags);
    setSuggestions({ summary: null, tags: null });
    showToast(
      "success",
      "Suggestions Accepted",
      "All AI recommendations have been applied.",
    );
  };

  const rejectAllSuggestions = () => {
    setSuggestions({ summary: null, tags: null });
    showToast(
      "info",
      "Suggestions Rejected",
      "All AI recommendations have been dismissed.",
    );
  };

  // Init: Fetch Categories
  const fetchCategories = async () => {
    setIsDataLoading(true);
    try {
      const data = await CategoryService.getCategories();
      setCategories(Object.keys(data));
    } catch (e) {
      showToast("error", "Fetch Error", "Failed to load categories.");
    } finally {
      setIsDataLoading(false);
    }
  };

  useEffect(() => {
    fetchCategories();
  }, []);

  // Selection Logic: Category
  const handleSelectCategory = async (id: string) => {
    setSelectedCategoryId(id);
    setSelectedAssetId(null);
    setFullCategoryContent(null);
    setFormData({ main_content: "", summary: "" });
    setTags([]);
    setSuggestions({ summary: null, tags: null });

    setIsDataLoading(true);
    try {
      const data = await CategoryService.getCategory(id);
      setFullCategoryContent(data.content);
    } catch (e) {
      showToast("error", "Fetch Error", "Failed to load category assets.");
    } finally {
      setIsDataLoading(false);
    }
  };

  // Selection Logic: Asset
  const handleSelectAsset = (assetId: string) => {
    setSelectedAssetId(assetId);
    const asset = fullCategoryContent.data[assetId];
    if (asset) {
      setFormData({
        main_content: asset.main_content || "",
        summary: asset.summary || "",
      });
      setTags(asset.tags || []);
      setSuggestions({ summary: null, tags: null });
    }
  };

  // AI Logic
  const handleSuggestAi = async () => {
    if (!formData.main_content) {
      showToast("alert", "Missing Content", "AI needs text to analyze.");
      return;
    }
    setIsAiLoading(true);
    try {
      const data = await AIService.getSuggestions({
        main_content: formData.main_content,
        summary: formData.summary,
        tags: tags,
      });

      setSuggestions({
        summary: data.summary || null,
        tags: data.tags || null,
      });
      showToast(
        "info",
        "AI Suggestions Ready",
        "Review recommended changes.",
      );
    } catch (e) {
      showToast("error", "AI Error", "Failed to fetch suggestions.");
    } finally {
      setIsAiLoading(false);
    }
  };

  const acceptSuggestion = (type: "summary" | "tags") => {
    if (type === "summary" && suggestions.summary) {
      setFormData((prev) => ({ ...prev, summary: suggestions.summary! }));
      setSuggestions((prev) => ({ ...prev, summary: null }));
    } else if (type === "tags" && suggestions.tags) {
      setTags(suggestions.tags);
      setSuggestions((prev) => ({ ...prev, tags: null }));
    }
  };

  const rejectSuggestion = (type: "summary" | "tags") => {
    setSuggestions((prev) => ({ ...prev, [type]: null }));
  };

  // CRUD: Save Changes
  const handleSave = async () => {
    if (!selectedCategoryId || !selectedAssetId) return;

    setIsDataLoading(true);
    try {
      await AssetService.updateAsset(selectedCategoryId, selectedAssetId, {
        main_content: formData.main_content,
        summary: formData.summary,
        tags: tags,
      });

      // Sync local fullCategoryContent for immediate UI update in Pane 2
      if (fullCategoryContent) {
        const updatedContent = { ...fullCategoryContent };
        updatedContent.data[selectedAssetId] = {
          ...updatedContent.data[selectedAssetId],
          main_content: formData.main_content,
          summary: formData.summary,
          tags: tags,
        };
        setFullCategoryContent(updatedContent);
      }

      // Clear selection and form as requested
      setSelectedAssetId(null);
      setFormData({ main_content: "", summary: "" });
      setTags([]);
      setSuggestions({ summary: null, tags: null });

      showToast(
        "success",
        "Asset Updated",
        "Changes saved and working area reset.",
      );
    } catch (e) {
      showToast("error", "Update Failed", e instanceof Error ? e.message : "Could not reach server.");
    } finally {
      setIsDataLoading(false);
    }
  };

  const handleDeleteAsset = () => {
    if (!selectedCategoryId || !selectedAssetId) return;
    setIsDeleteModalOpen(true);
  };

  const confirmDeleteAsset = async () => {
    if (!selectedCategoryId || !selectedAssetId) return;

    setIsDeleteModalOpen(false);
    setIsDataLoading(true);
    try {
      await AssetService.deleteAsset(selectedCategoryId, selectedAssetId);

      // Remove from local state
      const updatedContent = { ...fullCategoryContent };
      delete updatedContent.data[selectedAssetId];
      setFullCategoryContent(updatedContent);

      // Reset selection
      setSelectedAssetId(null);
      setFormData({ main_content: "", summary: "" });
      setTags([]);

      showToast(
        "alert",
        "Asset Deleted",
        "Asset was removed from the database.",
      );
    } catch (e) {
      showToast(
        "error",
        "Delete Error",
        e instanceof Error ? e.message : "Failed to remove asset.",
      );
    } finally {
      setIsDataLoading(false);
    }
  };

  const addTag = () => {
    if (currentTag.trim() && !tags.includes(currentTag.trim())) {
      setTags([...tags, currentTag.trim()]);
      setCurrentTag("");
    }
  };

  const removeTag = (t: string) => setTags(tags.filter((tag) => tag !== t));

  const hasPendingSuggestions =
    suggestions.summary !== null || suggestions.tags !== null;

  return (
    <div
      style={{
        display: "flex",
        gap: "20px",
        height: "calc(100vh - 100px)",
        maxWidth: "1600px",
        margin: "0 auto",
        overflow: "hidden",
      }}
    >
      {/* PANE 1: Categories */}
      <div
        style={{
          width: "240px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        <h2
          style={{
            fontSize: "0.8rem",
            fontWeight: 800,
            color: "#9ca3af",
            letterSpacing: "1px",
          }}
        >
          CATEGORIES
        </h2>
        <div
          className="scrollbar-hide"
          style={{
            flex: 1,
            overflowY: "auto",
            background: "rgba(255, 122, 26, 0.03)",
            padding: "12px",
            borderRadius: "16px",
            border: "1px solid rgba(255, 122, 26, 0.1)",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          {categories.map((id) => (
            <button
              key={id}
              onClick={() => handleSelectCategory(id)}
              style={{
                width: "100%",
                padding: "12px",
                borderRadius: "10px",
                textAlign: "left",
                border: "1px solid",
                borderColor:
                  selectedCategoryId === id ? "var(--accent)" : "rgba(255, 255, 255, 0.05)",
                background:
                  selectedCategoryId === id
                    ? "rgba(255, 122, 26, 0.1)"
                    : "transparent",
                color: selectedCategoryId === id ? "white" : "#9ca3af",
                fontSize: "0.85rem",
                fontWeight: selectedCategoryId === id ? 700 : 500,
                cursor: "pointer",
                transition: "all 0.2s",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <span>{formatCategoryName(id)}</span>
              {selectedCategoryId === id && (
                <ChevronRight size={14} color="var(--accent)" />
              )}
            </button>
          ))}
        </div>
      </div>

      {/* PANE 2: Assets List */}
      <div
        style={{
          width: "320px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        <h2
          style={{
            fontSize: "0.8rem",
            fontWeight: 800,
            color: "#9ca3af",
            letterSpacing: "1px",
          }}
        >
          ASSETS
        </h2>
        <div
          className="scrollbar-hide"
          style={{
            flex: 1,
            overflowY: "auto",
            background: "rgba(255, 122, 26, 0.02)",
            padding: "12px",
            borderRadius: "16px",
            border: "1px solid var(--glass-border)",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          {!selectedCategoryId ? (
            <div
              style={{
                height: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#4b5563",
                fontSize: "0.8rem",
                textAlign: "center",
                padding: "20px",
              }}
            >
              Select a category to view assets
            </div>
          ) : (
            <>
              {Object.keys(fullCategoryContent?.data || {}).length === 0 ? (
                <div
                  style={{
                    color: "#4b5563",
                    fontSize: "0.8rem",
                    textAlign: "center",
                    paddingTop: "40px",
                  }}
                >
                  No assets found.
                </div>
              ) : (
                Object.keys(fullCategoryContent.data).map((assetId) => {
                  const asset = fullCategoryContent.data[assetId];
                  return (
                    <button
                      key={assetId}
                      onClick={() => handleSelectAsset(assetId)}
                      style={{
                        width: "100%",
                        padding: "14px",
                        borderRadius: "12px",
                        border: "1px solid",
                        borderColor:
                          selectedAssetId === assetId
                            ? "var(--accent)"
                            : "rgba(255, 255, 255, 0.05)",
                        background:
                          selectedAssetId === assetId
                            ? "rgba(255, 122, 26, 0.05)"
                            : "rgba(255,255,255,0.01)",
                        textAlign: "left",
                        cursor: "pointer",
                        transition: "all 0.2s",
                        display: "flex",
                        alignItems: "center",
                        gap: "12px",
                      }}
                    >
                      <div style={{ flex: 1, overflow: "hidden" }}>
                        <div
                          style={{
                            fontSize: "0.75rem",
                            color: "var(--accent)",
                            fontWeight: 700,
                            marginBottom: "4px",
                          }}
                        >
                          ID: {assetId}
                        </div>
                        <div
                          style={{
                            fontSize: "0.85rem",
                            color:
                              selectedAssetId === assetId ? "white" : "#9ca3af",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            whiteSpace: "nowrap",
                          }}
                        >
                          {asset.main_content || "No Content"}
                        </div>
                        {asset.updated_at && (
                          <div
                            style={{
                              fontSize: "0.65rem",
                              color: "#4b5563",
                              marginTop: "6px",
                              display: "flex",
                              alignItems: "center",
                              gap: "4px",
                            }}
                          >
                            <Clock size={10} /> {formatDate(asset.updated_at)}
                          </div>
                        )}
                      </div>
                      {selectedAssetId === assetId && (
                        <ChevronRight size={16} color="var(--accent)" />
                      )}
                    </button>
                  );
                })
              )}
            </>
          )}
        </div>
      </div>

      {/* PANE 3: Form */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h2
            style={{
              fontSize: "0.8rem",
              fontWeight: 800,
              color: "#9ca3af",
              letterSpacing: "1px",
            }}
          >
            EDIT ASSET
          </h2>

          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            {selectedAssetId && (
              <>
                <button
                  onClick={clearForm}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    background: "rgba(255, 255, 255, 0.02)",
                    border: "1px solid var(--glass-border)",
                    color: "#9ca3af",
                    padding: "6px 12px",
                    borderRadius: "8px",
                    fontSize: "0.75rem",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  <RefreshCw size={12} /> CLEAR
                </button>

                <button
                  onClick={handleSuggestAi}
                  disabled={isAiLoading}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                    background: "rgba(255, 122, 26, 0.05)",
                    border: "1px solid var(--accent)",
                    color: "var(--accent)",
                    padding: "6px 12px",
                    borderRadius: "8px",
                    fontSize: "0.75rem",
                    fontWeight: 700,
                    cursor: "pointer",
                  }}
                >
                  {isAiLoading ? (
                    <Loader2 size={12} className="animate-spin" />
                  ) : (
                    <Sparkles size={12} />
                  )}
                  SUGGEST AI
                </button>

                {hasPendingSuggestions && (
                  <div style={{ display: "flex", gap: "6px" }}>
                    <button
                      onClick={rejectAllSuggestions}
                      style={{
                        background: "rgba(255,255,255,0.03)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        color: "#9ca3af",
                        padding: "6px 12px",
                        borderRadius: "8px",
                        fontSize: "0.75rem",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      REJECT ALL
                    </button>
                    <button
                      onClick={acceptAllSuggestions}
                      style={{
                        background: "#4ade80",
                        border: "none",
                        color: "#050505",
                        padding: "6px 12px",
                        borderRadius: "8px",
                        fontSize: "0.75rem",
                        fontWeight: 800,
                        cursor: "pointer",
                      }}
                    >
                      ACCEPT ALL
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>

        <div
          className="scrollbar-hide"
          style={{
            flex: 1,
            overflowY: "auto",
            background: "rgba(0,0,0,0.2)",
            padding: "24px",
            borderRadius: "24px",
            border: "1px solid rgba(255,255,255,0.05)",
            display: "flex",
            flexDirection: "column",
            gap: "24px",
          }}
        >
          {!selectedAssetId ? (
            <div
              style={{
                height: "100%",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                color: "#4b5563",
                gap: "12px",
              }}
            >
              <Database size={48} opacity={0.1} />
              <p style={{ fontSize: "0.9rem" }}>
                Select an asset to begin editing
              </p>
            </div>
          ) : (
            <>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: "16px",
                  marginBottom: "-8px",
                }}
              >
                <div
                  style={{
                    fontSize: "0.65rem",
                    fontWeight: 700,
                    color: "var(--accent)",
                    background: "rgba(255, 122, 26, 0.05)",
                    padding: "4px 10px",
                    borderRadius: "6px",
                    border: "1px solid rgba(255, 122, 26, 0.1)",
                  }}
                >
                  ASSET ID: {selectedAssetId}
                </div>
                {fullCategoryContent.data[selectedAssetId]?.created_at && (
                  <div
                    style={{
                      fontSize: "0.65rem",
                      fontWeight: 600,
                      color: "#6b7280",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <Calendar size={12} /> CREATED ON:{" "}
                    {formatDate(
                      fullCategoryContent.data[selectedAssetId].created_at,
                    )}
                  </div>
                )}
                {fullCategoryContent.data[selectedAssetId]?.updated_at && (
                  <div
                    style={{
                      fontSize: "0.65rem",
                      fontWeight: 600,
                      color: "#6b7280",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <Clock size={12} /> LAST UPDATED:{" "}
                    {formatDate(
                      fullCategoryContent.data[selectedAssetId].updated_at,
                    )}
                  </div>
                )}
              </div>

              {/* Content Field */}
              <div
                style={{ display: "flex", flexDirection: "column", gap: "8px" }}
              >
                <label
                  style={{
                    fontSize: "0.7rem",
                    fontWeight: 800,
                    color: "#4b5563",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <FileText size={12} /> MAIN CONTENT
                </label>
                <textarea
                  value={formData.main_content}
                  onChange={(e) =>
                    setFormData({ ...formData, main_content: e.target.value })
                  }
                  rows={4}
                  style={{
                    padding: "14px",
                    background: "rgba(255,255,255,0.02)",
                    border: "1px solid var(--glass-border)",
                    borderRadius: "12px",
                    color: "white",
                    fontSize: "0.9rem",
                    resize: "none",
                    outline: "none",
                  }}
                />
              </div>

              {/* Summary Field + Suggestion */}
              <div
                style={{ display: "flex", flexDirection: "column", gap: "8px" }}
              >
                <label
                  style={{
                    fontSize: "0.7rem",
                    fontWeight: 800,
                    color: "#4b5563",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <Layout size={12} /> SUMMARY
                </label>
                <textarea
                  value={formData.summary}
                  onChange={(e) =>
                    setFormData({ ...formData, summary: e.target.value })
                  }
                  rows={3}
                  style={{
                    padding: "14px",
                    background: "rgba(255,255,255,0.02)",
                    border: "1px solid var(--glass-border)",
                    borderRadius: "12px",
                    color: "white",
                    fontSize: "0.9rem",
                    resize: "none",
                    outline: "none",
                  }}
                />
                <AnimatePresence>
                  {suggestions.summary && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      style={{
                        background: "rgba(74, 222, 128, 0.05)",
                        border: "1px dashed #4ade80",
                        borderRadius: "12px",
                        padding: "12px",
                        marginTop: "8px",
                      }}
                    >
                      <div
                        style={{
                          color: "#4ade80",
                          fontSize: "0.7rem",
                          fontWeight: 800,
                          marginBottom: "8px",
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                        }}
                      >
                        <Sparkles size={12} /> AI RECOMMENDED SUMMARY
                      </div>
                      <p
                        style={{
                          fontSize: "0.8rem",
                          color: "white",
                          marginBottom: "10px",
                          lineHeight: 1.6,
                        }}
                      >
                        {suggestions.summary}
                      </p>
                      <div style={{ display: "flex", gap: "8px" }}>
                        <button
                          onClick={() => acceptSuggestion("summary")}
                          style={{
                            fontSize: "0.7rem",
                            background: "#4ade80",
                            color: "black",
                            border: "none",
                            padding: "6px 12px",
                            borderRadius: "6px",
                            fontWeight: 700,
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          <ThumbsUp size={12} /> Accept
                        </button>
                        <button
                          onClick={() => rejectSuggestion("summary")}
                          style={{
                            fontSize: "0.7rem",
                            background: "rgba(255,255,255,0.05)",
                            color: "white",
                            border: "1px solid rgba(255,255,255,0.1)",
                            padding: "6px 12px",
                            borderRadius: "6px",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          <ThumbsDown size={12} /> Reject
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Tags Field */}
              <div
                style={{ display: "flex", flexDirection: "column", gap: "8px" }}
              >
                <label
                  style={{
                    fontSize: "0.7rem",
                    fontWeight: 800,
                    color: "#4b5563",
                    display: "flex",
                    alignItems: "center",
                    gap: "6px",
                  }}
                >
                  <Hash size={12} /> KEYWORDS
                </label>
                <div style={{ display: "flex", gap: "8px" }}>
                  <input
                    value={currentTag}
                    onChange={(e) => setCurrentTag(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && addTag()}
                    placeholder="Add tag..."
                    style={{
                      flex: 1,
                      padding: "10px 14px",
                      background: "rgba(255,255,255,0.02)",
                      border: "1px solid var(--glass-border)",
                      borderRadius: "10px",
                      color: "white",
                      fontSize: "0.85rem",
                      outline: "none",
                    }}
                  />
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {tags.map((t) => (
                    <span
                      key={t}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        background: "rgba(255, 122, 26, 0.1)",
                        padding: "4px 10px",
                        borderRadius: "6px",
                        fontSize: "0.75rem",
                        color: "white",
                      }}
                    >
                      {t}{" "}
                      <X
                        size={10}
                        onClick={() => removeTag(t)}
                        style={{ cursor: "pointer" }}
                      />
                    </span>
                  ))}
                </div>
              </div>

              {/* Action Bar */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "12px",
                  marginTop: "auto",
                  paddingTop: "20px",
                }}
              >
                <button
                  onClick={handleDeleteAsset}
                  disabled={isDataLoading}
                  style={{
                    background: "rgba(255, 77, 77, 0.05)",
                    color: "#ff4d4d",
                    border: "1px solid rgba(255, 77, 77, 0.2)",
                    padding: "10px 20px",
                    borderRadius: "10px",
                    fontWeight: 700,
                    fontSize: "0.8rem",
                    cursor: isDataLoading ? "not-allowed" : "pointer",
                  }}
                >
                  <Trash2 size={14} />
                </button>
                <button
                  onClick={handleSave}
                  disabled={isDataLoading || hasPendingSuggestions}
                  style={{
                    background:
                      isDataLoading || hasPendingSuggestions
                        ? "rgba(255,255,255,0.05)"
                        : "var(--accent)",
                    color:
                      isDataLoading || hasPendingSuggestions
                        ? "#4b5563"
                        : "white",
                    border: "none",
                    padding: "10px 32px",
                    borderRadius: "10px",
                    fontWeight: 800,
                    fontSize: "0.8rem",
                    cursor:
                      isDataLoading || hasPendingSuggestions
                        ? "not-allowed"
                        : "pointer",
                    boxShadow:
                      isDataLoading || hasPendingSuggestions
                        ? "none"
                        : "0 4px 15px rgba(255, 122, 26, 0.2)",
                  }}
                >
                  {isDataLoading ? (
                    <Loader2 className="animate-spin" size={14} />
                  ) : (
                    "SAVE CHANGES"
                  )}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <ConfirmModal
        isOpen={isDeleteModalOpen}
        title="Delete Asset?"
        message="Are you sure you want to permanently delete this asset? This action cannot be undone."
        confirmText="Delete"
        onConfirm={confirmDeleteAsset}
        onCancel={() => setIsDeleteModalOpen(false)}
      />
    </div>
  );
};

export default ManageAssets;
