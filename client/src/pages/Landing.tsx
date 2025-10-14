import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Check, Database, Sparkles, Shield, Zap, BarChart3, FileText, Globe, Linkedin, Github, ExternalLink, Book } from "lucide-react";
import { api } from "@/lib/api";

const features = [
  {
    icon: Database,
    title: "Connect any CSV/SQLite",
    description: "Upload CSV/Excel and query instantly with an embedded SQLite engine.",
  },
  {
    icon: Book,
    title: "Notion Integration",
    description: "Connect your Notion workspace and query your knowledge base using natural language through MCP.",
  },
  {
    icon: Sparkles,
    title: "Reasoning + Tools",
    description: "The agent reasons, calls tools, and explains its steps concisely.",
  },
  {
    icon: Shield,
    title: "Private by Design",
    description: "Runs behind your API with server-side streaming and secure file handling.",
  },
  {
    icon: Zap,
    title: "Real-time Streaming",
    description: "Watch AI responses stream in real-time with live tool execution visibility.",
  },
  {
    icon: BarChart3,
    title: "Data Insights",
    description: "Generate charts, summaries, and actionable insights from your data instantly.",
  },
  {
    icon: FileText,
    title: "Natural Language Queries",
    description: "Ask questions in plain English - no SQL knowledge required.",
  },
];

const useCases = [
  {
    title: "Business Analytics",
    description: "Analyze sales data, track KPIs, and generate reports with simple conversational queries.",
  },
  {
    title: "Knowledge Management",
    description: "Query your Notion workspace, search documentation, and retrieve information from your knowledge base effortlessly.",
  },
  {
    title: "Data Exploration",
    description: "Discover patterns, outliers, and trends in your datasets through natural dialogue.",
  },
  {
    title: "Quick Insights",
    description: "Get instant answers about your data without writing complex SQL queries.",
  },
];

const Landing = () => {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.me().then((r) => {
      if (r.username) navigate("/chat");
    }).catch(() => {});
  }, [navigate]);

  const handleAuth = async (mode: "signin" | "signup") => {
    if (!username || !password) return;
    setLoading(true);
    try {
      if (mode === "signup") await api.signup(username, password);
      else await api.signin(username, password);
      navigate("/chat");
    } catch (e: any) {
      alert(e?.message || "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#121212] text-foreground">
      <div className="relative overflow-hidden">
        {/* Hero */}
        <section className="px-6 md:px-10 pt-20 pb-12 md:pt-28 md:pb-16">
          <div className="max-w-6xl mx-auto grid md:grid-cols-2 gap-10 items-center">
            <div>
              <h1 className="text-3xl md:text-5xl font-extrabold tracking-tight">
                Meet your AI Database Assistant
              </h1>
              <p className="mt-4 text-base md:text-lg text-muted-foreground">
                Upload your data, connect your Notion workspace, and chat to explore insights, run
                analysis, and retrieve knowledge with AI-powered tool-assisted reasoning.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <Link to="/auth">
                  <Button className="h-10 px-5 text-sm">Get Started Free</Button>
                </Link>
                <a href="#features">
                  <Button variant="outline" className="h-10 px-5 text-sm">Learn more</Button>
                </a>
              </div>
              <ul className="mt-6 space-y-2 text-sm text-muted-foreground">
                <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> Streaming responses</li>
                <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> Notion workspace integration</li>
                <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> Tool call visibility</li>
                <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> Beautiful dark UI</li>
              </ul>
            </div>
            <div className="flex items-center justify-center">
              <img 
                src="/herologo2.png" 
                alt="Qbit Agent Logo" 
                className="w-full h-auto max-w-lg"
              />
            </div>
          </div>
        </section>

        {/* Features */}
        <section id="features" className="px-6 md:px-10 pb-16">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-2xl md:text-3xl font-bold">Powerful Features</h2>
              <p className="mt-3 text-muted-foreground max-w-2xl mx-auto">
                Everything you need to interact with your data using natural language and AI
              </p>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
              {features.map(({ icon: Icon, title, description }, i) => (
                <Card key={i} className="p-5 bg-[#1b1b1b] border-white/10 hover:border-white/20 transition-colors">
                  <div className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
                    <Icon className="h-4 w-4" />
                  </div>
                  <h3 className="mt-3 text-base font-semibold">{title}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{description}</p>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* Use Cases */}
        <section className="px-6 md:px-10 pb-16">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-2xl md:text-3xl font-bold">Perfect For</h2>
              <p className="mt-3 text-muted-foreground max-w-2xl mx-auto">
                Whether you're analyzing business data or exploring datasets, Qbit Agent has you covered
              </p>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
              {useCases.map((useCase, i) => (
                <Card key={i} className="p-6 bg-[#1b1b1b] border-white/10">
                  <h3 className="text-lg font-semibold mb-2">{useCase.title}</h3>
                  <p className="text-sm text-muted-foreground">{useCase.description}</p>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* Pricing */}
        <section id="pricing" className="px-6 md:px-10 pb-16">
          <div className="max-w-6xl mx-auto">
            <div className="text-center mb-12">
              <h2 className="text-2xl md:text-3xl font-bold">Simple, transparent pricing</h2>
              <p className="mt-3 text-muted-foreground max-w-2xl mx-auto">
                Start free. Upgrade when you need more power, speed, and features.
              </p>
            </div>
            <div className="grid md:grid-cols-3 gap-6">
              {/* Free */}
              <Card className="p-6 bg-[#1b1b1b] border-white/10 flex flex-col">
                <div>
                  <h3 className="text-lg font-semibold">Free</h3>
                  <p className="mt-1 text-sm text-muted-foreground">For personal exploration</p>
                  <div className="mt-4 flex items-baseline gap-1">
                    <span className="text-3xl font-extrabold">$0</span>
                    <span className="text-muted-foreground">/mo</span>
                  </div>
                </div>
                <ul className="mt-5 space-y-2 text-sm text-muted-foreground flex-1">
                  <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> 1,000 tokens / chat</li>
                  <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> CSV/Excel uploads</li>
                  <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> Basic charts</li>
                </ul>
                <div className="mt-6">
                  <Link to="/auth">
                    <Button className="w-full">Get started</Button>
                  </Link>
                </div>
              </Card>

              {/* Pro */}
              <Card className="p-6 bg-[#202020] border-white/20 shadow-lg ring-1 ring-white/10 flex flex-col">
                <div>
                  <div className="inline-block rounded-full px-2 py-0.5 text-[10px] bg-primary/20 text-primary border border-primary/30">Most popular</div>
                  <h3 className="mt-2 text-lg font-semibold">Pro</h3>
                  <p className="mt-1 text-sm text-muted-foreground">For analysts & teams</p>
                  <div className="mt-4 flex items-baseline gap-1">
                    <span className="text-3xl font-extrabold">$19</span>
                    <span className="text-muted-foreground">/mo</span>
                  </div>
                </div>
                <ul className="mt-5 space-y-2 text-sm text-muted-foreground flex-1">
                  <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> 20,000 tokens / chat</li>
                  <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> Priority streaming</li>
                  <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> Advanced charting</li>
                  <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> Per-user data isolation</li>
                </ul>
                <div className="mt-6">
                  <Link to="/auth">
                    <Button className="w-full">Upgrade to Pro</Button>
                  </Link>
                </div>
              </Card>

              {/* Enterprise */}
              <Card className="p-6 bg-[#1b1b1b] border-white/10 flex flex-col">
                <div>
                  <h3 className="text-lg font-semibold">Enterprise</h3>
                  <p className="mt-1 text-sm text-muted-foreground">For production workloads</p>
                  <div className="mt-4 flex items-baseline gap-1">
                    <span className="text-3xl font-extrabold">Custom</span>
                  </div>
                </div>
                <ul className="mt-5 space-y-2 text-sm text-muted-foreground flex-1">
                  <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> SSO & custom auth</li>
                  <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> Dedicated support</li>
                  <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> On-prem / VPC ready</li>
                  <li className="flex items-center gap-2"><Check className="h-4 w-4 text-success" /> SLAs & security reviews</li>
                </ul>
                <div className="mt-6">
                  <Link to="/auth">
                    <Button variant="outline" className="w-full">Contact sales</Button>
                  </Link>
                </div>
              </Card>
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="px-6 md:px-10 pb-20">
          <div className="max-w-4xl mx-auto">
            <Card className="p-8 md:p-12 bg-[#1b1b1b] from-primary/10 to-primary/5 border-primary/20 text-center">
              <h2 className="text-2xl md:text-3xl font-bold mb-4">Ready to explore your data?</h2>
              <p className="text-muted-foreground mb-6 max-w-xl mx-auto">
                Start chatting with your data in seconds. No setup required, just upload and ask.
              </p>
              <Link to="/auth">
                <Button size="lg" className="h-12 px-8 text-base">
                  Get Started Now
                </Button>
              </Link>
            </Card>
          </div>
        </section>

        {/* Footer */}
        <footer className="border-t border-white/10 bg-[#0a0a0a]">
          <div className="max-w-6xl mx-auto px-6 md:px-10 py-12">
            <div className="grid md:grid-cols-2 gap-8 items-center">
              <div>
                <h3 className="text-xl font-bold mb-2">Qbit Agent</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  AI-powered database assistant for natural language data queries
                </p>
                <p className="text-sm text-muted-foreground">
                  Developed by <span className="text-foreground font-semibold">Zain Sheikh</span>
                </p>
              </div>
              <div className="flex flex-col items-start md:items-end gap-4">
                <div className="flex flex-wrap gap-3">
                  <a
                    href="https://zainafzal.dev"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 transition-colors text-sm"
                  >
                    <Globe className="h-4 w-4" />
                    <span>Website</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                  <a
                    href="https://linkedin.com/in/muhammad-zain-afzal"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 transition-colors text-sm"
                  >
                    <Linkedin className="h-4 w-4" />
                    <span>LinkedIn</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                  <a
                    href="https://github.com/sheikhmuhammadzain"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 transition-colors text-sm"
                  >
                    <Github className="h-4 w-4" />
                    <span>GitHub</span>
                    <ExternalLink className="h-3 w-3" />
                  </a>
                </div>
                <p className="text-xs text-muted-foreground">
                  © {new Date().getFullYear()} Zain Sheikh. All rights reserved.
                </p>
              </div>
            </div>
          </div>
        </footer>
      </div>
    </div>
  );
};

export default Landing;



