import { Badge } from "@/components/ui/badge";
import { Loader2, Copy, ThumbsUp, ThumbsDown, RotateCw, MoreHorizontal, ChevronDown, ChevronUp, Lightbulb } from "lucide-react";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, LineChart, Line, AreaChart, Area, PieChart, Pie, Cell, CartesianGrid, Legend, LabelList } from "recharts";

function ChartRenderer({ spec }: { spec: any }) {
  const data = Array.isArray(spec?.data) ? spec.data : [];
  const xKey = spec?.x;
  const yKey = spec?.y;
  const chartType = spec?.chart || "bar";
  const colors = ["#60a5fa", "#f59e0b", "#34d399", "#f472b6", "#a78bfa"]; 
  if (!xKey || !yKey || !data.length) {
    return <pre className="whitespace-pre-wrap break-words">{JSON.stringify(spec, null, 2)}</pre>;
  }
  return (
    <div className="bg-black/20 rounded p-2">
      <div className="text-[10px] mb-1 text-muted-foreground">Chart preview</div>
      <div style={{ width: "100%", height: 220 }}>
        <ResponsiveContainer>
          {chartType === "line" ? (
            <LineChart data={data}>
              <CartesianGrid stroke="#2a2a2a" strokeDasharray="3 3" />
              <XAxis dataKey={xKey} stroke="#9CA3AF" tick={{ fontSize: 10 }} label={{ value: xKey, position: "insideBottom", offset: -5, fill: "#9CA3AF", fontSize: 10 }} />
              <YAxis stroke="#9CA3AF" tick={{ fontSize: 10 }} label={{ value: yKey, angle: -90, position: "insideLeft", fill: "#9CA3AF", fontSize: 10 }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey={yKey} stroke="#60a5fa" strokeWidth={2} dot={{ r: 2 }} label={{ position: "top", fill: "#e5e7eb", fontSize: 10 }} />
            </LineChart>
          ) : chartType === "area" ? (
            <AreaChart data={data}>
              <CartesianGrid stroke="#2a2a2a" strokeDasharray="3 3" />
              <XAxis dataKey={xKey} stroke="#9CA3AF" tick={{ fontSize: 10 }} label={{ value: xKey, position: "insideBottom", offset: -5, fill: "#9CA3AF", fontSize: 10 }} />
              <YAxis stroke="#9CA3AF" tick={{ fontSize: 10 }} label={{ value: yKey, angle: -90, position: "insideLeft", fill: "#9CA3AF", fontSize: 10 }} />
              <Tooltip />
              <Legend />
              <Area type="monotone" dataKey={yKey} stroke="#60a5fa" fill="#60a5fa55" />
            </AreaChart>
          ) : chartType === "pie" ? (
            <PieChart>
              <Tooltip />
              <Legend />
              <Pie data={data} dataKey={yKey} nameKey={xKey} outerRadius={80} label={({ name, value }) => `${name}: ${value}` } labelLine={false}>
                {data.map((_: any, idx: number) => (
                  <Cell key={`c-${idx}`} fill={colors[idx % colors.length]} />
                ))}
              </Pie>
            </PieChart>
          ) : (
            <BarChart data={data}>
              <CartesianGrid stroke="#2a2a2a" strokeDasharray="3 3" />
              <XAxis dataKey={xKey} stroke="#9CA3AF" tick={{ fontSize: 10 }} label={{ value: xKey, position: "insideBottom", offset: -5, fill: "#9CA3AF", fontSize: 10 }} />
              <YAxis stroke="#9CA3AF" tick={{ fontSize: 10 }} label={{ value: yKey, angle: -90, position: "insideLeft", fill: "#9CA3AF", fontSize: 10 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey={yKey} fill="#60a5fa">
                <LabelList dataKey={yKey} position="top" fill="#e5e7eb" fontSize={10} />
              </Bar>
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
import type { Message as MessageType } from "@/pages/Index";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
// Internal lightweight chart renderer (kept local to avoid cross-file coupling)

interface MessageProps {
  message: MessageType;
}

export const Message = ({ message }: MessageProps) => {
  const isUser = message.role === "user";
  const [showReasoning, setShowReasoning] = useState(false);
  const [showToolDetails, setShowToolDetails] = useState<{ [key: number]: boolean }>({});
  const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);
  const { toast } = useToast();

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content || "");
      toast({ title: "Copied to clipboard" });
    } catch {}
  };

  const handleCopyReasoning = async () => {
    try {
      await navigator.clipboard.writeText(message.reasoning || "");
      toast({ title: "Thoughts copied" });
    } catch {}
  };

  const handleThumbsUp = () => {
    setFeedback(feedback === 'up' ? null : 'up');
    toast({ 
      title: feedback === 'up' ? "Feedback removed" : "Thanks for your feedback!",
      description: feedback === 'up' ? "" : "This helps improve the AI responses"
    });
  };

  const handleThumbsDown = () => {
    setFeedback(feedback === 'down' ? null : 'down');
    toast({ 
      title: feedback === 'down' ? "Feedback removed" : "Thanks for your feedback!",
      description: feedback === 'down' ? "" : "We'll work on improving this"
    });
  };

  const handleRegenerate = () => {
    toast({ 
      title: "Regenerate response",
      description: "This feature will be available soon",
      variant: "default"
    });
  };

  const handleMore = () => {
    toast({ 
      title: "More options",
      description: "Additional options coming soon",
      variant: "default"
    });
  };

  if (isUser) {
    // User message - bubble on the right
    return (
      <div className="w-full px-3 sm:px-6 py-4 sm:py-6 flex justify-end">
        <div className="max-w-[85%] sm:max-w-[70%]">
          <div className="bg-[#2f2f2f] text-foreground rounded-3xl px-4 sm:px-5 py-2.5 sm:py-3 inline-block">
            <p className="text-[14px] sm:text-[15px] leading-6 sm:leading-7 whitespace-pre-wrap">{message.content}</p>
          </div>
        </div>
      </div>
    );
  }

  // AI message - left-aligned without background
  return (
    <div className="w-full px-3 sm:px-16 py-4 sm:py-6">
      <div className="max-w-full sm:max-w-3xl">
          <div className="space-y-3">
            {/* Reasoning panel - Polished UI */}
            {message.reasoning && (
              <div className="text-xs">
                <div
                  className="group rounded-xl border border-white/10 bg-white/5"
                >
                  <div className="flex items-center justify-between px-3 py-2">
                    <button
                      onClick={() => setShowReasoning(!showReasoning)}
                      className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
                      aria-expanded={showReasoning}
                    >
                      <span className="inline-flex h-5 w-5 items-center justify-center rounded-md bg-white/10 text-muted-foreground">
                        <Lightbulb className="h-3.5 w-3.5" />
                      </span>
                      <span className="font-medium">Thoughts</span>
                      <span className="ml-2 rounded-full bg-white/10 px-2 py-0.5 text-[10px] text-muted-foreground">
                        {Math.ceil(message.reasoning.length / 50)}s
                      </span>
                      <span className={`ml-2 transition-transform ${showReasoning ? "rotate-180" : ""}`}>
                        <ChevronDown className="h-3.5 w-3.5" />
                      </span>
                    </button>
                    <button
                      onClick={handleCopyReasoning}
                      className="text-muted-foreground hover:text-foreground transition-colors"
                      aria-label="Copy thoughts"
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  {showReasoning && (
                    <div className="px-3 pb-3">
                      <div className="rounded-lg border border-white/10 bg-black/20 p-3 max-h-72 overflow-y-auto scrollbar-thin">
                        <div className="text-[11px] leading-relaxed text-muted-foreground/80 space-y-2">
                          <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                              p: ({children}) => <p className="my-1">{children}</p>,
                              code: ({children}) => <code className="text-[10px] bg-white/5 px-1 rounded">{children}</code>
                            }}
                          >
                            {message.reasoning}
                          </ReactMarkdown>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Tool Calls - Minimal, neutral styling */}
            {message.toolCalls && message.toolCalls.length > 0 && (
              <div className="space-y-2 text-xs">
                {message.toolCalls.map((tool, index) => (
                  <div key={index} className="rounded-lg border border-white/10 bg-white/5">
                    <div className="flex items-center justify-between px-3 py-1.5 text-muted-foreground">
                    <button
                        onClick={() => setShowToolDetails({ ...showToolDetails, [index]: !showToolDetails[index] })}
                        className="inline-flex items-center gap-2 hover:text-foreground transition-colors"
                        aria-expanded={!!showToolDetails[index]}
                      >
                        {tool.status === "executing" && <Loader2 className="h-3 w-3 animate-spin" />}
                        {tool.status === "done" && <span className="text-foreground/70">✓</span>}
                      <span className="font-mono text-[11px]">
                        MCP tool called: {tool.name}
                      </span>
                        <span className={`transition-transform ${showToolDetails[index] ? "rotate-180" : ""}`}>
                          <ChevronDown className="h-3.5 w-3.5" />
                        </span>
                      </button>
                    </div>

                    {showToolDetails[index] && (tool.arguments || tool.result) && (
                      <div className="px-3 pb-3 space-y-2">
                        {tool.arguments && (
                          <div className="rounded border border-white/10 bg-black/20">
                            <div className="px-2 pt-2 text-[11px] text-muted-foreground">Input</div>
                            <pre className="m-2 mt-1 text-[10px] text-muted-foreground/90 whitespace-pre-wrap rounded p-2 bg-black/30 overflow-x-auto scrollbar-thin">
                              {JSON.stringify(tool.arguments, null, 2)}
                            </pre>
                          </div>
                        )}
                        {tool.result && (
                          <div className="rounded border border-white/10 bg-black/20">
                            <div className="px-2 pt-2 text-[11px] text-muted-foreground">Result</div>
                            <div className="m-2 mt-1 text-[10px] text-muted-foreground/90 max-h-60 overflow-y-auto scrollbar-thin bg-black/30 rounded p-2.5 leading-relaxed font-mono">
                              {(() => {
                                const val: any = tool.result;
                                // Helper to attempt multiple parse strategies
                                const tryParses = (s: string) => {
                                  // 1) direct parse
                                  try { return JSON.parse(s); } catch {}
                                  // 2) trim to first/last brace
                                  try {
                                    const start = s.indexOf('{');
                                    const end = s.lastIndexOf('}');
                                    if (start !== -1 && end !== -1 && end > start) {
                                      const sliced = s.slice(start, end + 1);
                                      return JSON.parse(sliced);
                                    }
                                  } catch {}
                                  // 3) if it looks like a JSON string escaped once
                                  try {
                                    const unescaped = s
                                      .replace(/\\n/g, '\n')
                                      .replace(/\\"/g, '"')
                                      .replace(/\\t/g, '\t');
                                    return JSON.parse(unescaped);
                                  } catch {}
                                  return null;
                                };

                                try {
                                  let parsed = typeof val === 'string' ? tryParses(val) : (typeof val === 'object' ? val : null);
                                  
                                  // Handle nested result objects (e.g., {result: "{...}"})
                                  if (parsed && typeof parsed === 'object' && 'result' in parsed && typeof parsed.result === 'string') {
                                    try {
                                      const innerParsed = tryParses(parsed.result);
                                      if (innerParsed) {
                                        console.log("Unwrapped nested result:", innerParsed);
                                        parsed = innerParsed;
                                      }
                                    } catch (e) {
                                      console.warn("Failed to parse nested result:", e);
                                    }
                                  }
                                  
                                  if (parsed) {
                                    console.log("✅ Parsed tool result:", { type: parsed.type, hasSpec: !!parsed.spec, parsed });
                                    
                                    // Check for chart specification
                                    if (parsed && typeof parsed === 'object' && parsed.type === 'chart' && parsed.spec) {
                                      console.log("📊 Rendering chart with spec:", parsed.spec);
                                      return (
                                        <div className="not-prose -mx-2.5 -mb-2.5">
                                          <ChartRenderer spec={parsed.spec} />
                                        </div>
                                      );
                                    }
                                    
                                    // Pretty print JSON
                                    return <pre className="whitespace-pre-wrap break-words">{JSON.stringify(parsed, null, 2)}</pre>;
                                  }
                                  
                                  console.warn("❌ No valid parsed result, falling back");
                                } catch (e) {
                                  console.error("💥 Error in tool result rendering:", e);
                                }

                                // Final fallback: render as markdown/plain text for visibility
                                try { console.warn("tool_result_json_parse_failed_raw", val); } catch {}
                                const printable = typeof val === 'string' ? val : JSON.stringify(val, null, 2);
                                return (
                                  <ReactMarkdown remarkPlugins={[remarkGfm]} className="prose prose-xs dark:prose-invert max-w-none prose-p:text-[10px] prose-code:text-[9px]">
                                    {printable}
                                  </ReactMarkdown>
                                );
                              })()}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

          {/* AI Response */}
          {(() => {
            const MarkdownBlock = ({ text }: { text: string }) => (
              <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-7 prose-pre:bg-black/40 prose-pre:border prose-pre:border-border prose-pre:overflow-x-auto prose-pre:scrollbar-thin">
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight as any]}>
                  {text}
                </ReactMarkdown>
              </div>
            );

            const tryParses = (s: string) => {
              try { return JSON.parse(s); } catch {}
              try {
                const start = s.indexOf('{');
                const end = s.lastIndexOf('}');
                if (start !== -1 && end !== -1 && end > start) {
                  const sliced = s.slice(start, end + 1);
                  return JSON.parse(sliced);
                }
              } catch {}
              try {
                const unescaped = s
                  .replace(/\\n/g, '\n')
                  .replace(/\\"/g, '"')
                  .replace(/\\t/g, '\t');
                return JSON.parse(unescaped);
              } catch {}
              return null;
            };

            const renderWithEmbeddedCharts = (content: string) => {
              const nodes: any[] = [];
              const regex = /<chart([^>]*)>([\s\S]*?)<\/chart>/gi;
              let lastIndex = 0; let match: RegExpExecArray | null;
              while ((match = regex.exec(content)) !== null) {
                const before = content.slice(lastIndex, match.index);
                if (before) nodes.push(<MarkdownBlock key={`md-${lastIndex}` } text={before} />);

                const attrs = match[1] || ""; const inner = match[2] || "";
                const attrMap: Record<string, string> = {};
                const attrRe = /(\w+)\s*=\s*"([^"]*)"/g; let am: RegExpExecArray | null;
                while ((am = attrRe.exec(attrs)) !== null) { attrMap[am[1]] = am[2]; }

                let spec: any | null = null;
                const parsedInner = tryParses(inner);
                if (parsedInner) {
                  if (parsedInner.type === 'chart' && parsedInner.spec) {
                    spec = parsedInner.spec;
                  } else if (parsedInner.spec) {
                    spec = parsedInner.spec;
                  } else if (Array.isArray(parsedInner)) {
                    spec = { chart: attrMap.type || 'bar', x: attrMap.x, y: attrMap.y, data: parsedInner };
                  } else if (parsedInner.data) {
                    spec = {
                      chart: attrMap.type || parsedInner.chart || 'bar',
                      x: attrMap.x || parsedInner.x,
                      y: attrMap.y || parsedInner.y,
                      data: parsedInner.data
                    };
                  } else {
                    // assume it's already a spec-like object
                    spec = parsedInner;
                  }
                }

                if (spec && spec.x && spec.y && Array.isArray(spec.data)) {
                  nodes.push(
                    <div key={`chart-${match.index}`} className="not-prose my-2">
                      <ChartRenderer spec={spec} />
                    </div>
                  );
                } else {
                  // Fallback to show block as-is
                  nodes.push(<MarkdownBlock key={`md-fallback-${match.index}`} text={match[0]} />);
                }

                lastIndex = match.index + match[0].length;
              }

              const tail = content.slice(lastIndex);
              if (tail) nodes.push(<MarkdownBlock key={`md-tail-${lastIndex}`} text={tail} />);
              return nodes;
            };

            const rendered = renderWithEmbeddedCharts(message.content || "");
            return (
              <div>
                {rendered}
                {message.isStreaming && (
                  <Loader2 className="inline-block ml-2 h-4 w-4 animate-spin text-muted-foreground" />
                )}
              </div>
            );
          })()}

          {/* Action Buttons - ChatGPT Style */}
          {!message.isStreaming && message.content && (
            <div className="flex items-center gap-0.5 sm:gap-1 mt-2 sm:mt-3 flex-wrap">
              <Button
                variant="ghost"
                size="icon"
                onClick={handleCopy}
                className="h-6 w-6 sm:h-7 sm:w-7 rounded-lg hover:bg-white/5"
                title="Copy"
              >
                <Copy className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleThumbsUp}
                className={`h-6 w-6 sm:h-7 sm:w-7 rounded-lg hover:bg-white/5 ${feedback === 'up' ? 'text-success bg-success/10' : ''}`}
                title="Good response"
              >
                <ThumbsUp className={`h-3 w-3 sm:h-3.5 sm:w-3.5 ${feedback === 'up' ? 'fill-current' : ''}`} />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleThumbsDown}
                className={`h-6 w-6 sm:h-7 sm:w-7 rounded-lg hover:bg-white/5 ${feedback === 'down' ? 'text-destructive bg-destructive/10' : ''}`}
                title="Bad response"
              >
                <ThumbsDown className={`h-3 w-3 sm:h-3.5 sm:w-3.5 ${feedback === 'down' ? 'fill-current' : ''}`} />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleRegenerate}
                className="h-6 w-6 sm:h-7 sm:w-7 rounded-lg hover:bg-white/5"
                title="Regenerate"
              >
                <RotateCw className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleMore}
                className="h-6 w-6 sm:h-7 sm:w-7 rounded-lg hover:bg-white/5 hidden sm:inline-flex"
                title="More"
              >
                <MoreHorizontal className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
