/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        /* Surface elevation scale */
        surface: {
          0: "hsl(var(--surface-0, var(--background)))",
          1: "hsl(var(--surface-1, var(--card)))",
          2: "hsl(var(--surface-2, var(--secondary)))",
          3: "hsl(var(--surface-3, var(--accent)))",
        },
        /* Semantic accent aliases */
        "accent-emerald": "hsl(var(--accent-emerald, 158 64% 52%))",
        "accent-amber": "hsl(var(--accent-amber, 38 92% 50%))",
        "accent-crimson": "hsl(var(--accent-crimson, 0 72% 51%))",
        "accent-violet": "hsl(var(--accent-violet, 263 70% 50%))",
        "accent-blue": "hsl(var(--accent-blue, 217 91% 60%))",
        /* Graph node colors */
        graph: {
          decision: "#3b82f6",
          assumption: "#f59e0b",
          evidence: "#10b981",
          task: "#8b5cf6",
          approval: "#ef4444",
          person: "#64748b",
          meeting: "#0ea5e9",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains-mono)", "Menlo", "monospace"],
      },
      fontSize: {
        /* Enforce 16px minimum — all small sizes map to 1rem */
        xs: ["1rem", { lineHeight: "1.5" }],          /* 16px (was 12px) */
        sm: ["1rem", { lineHeight: "1.5" }],          /* 16px (was 14px) */
        base: ["1rem", { lineHeight: "1.6" }],        /* 16px */
        lg: ["1.125rem", { lineHeight: "1.5" }],      /* 18px */
        xl: ["1.25rem", { lineHeight: "1.4" }],       /* 20px */
        "2xl": ["1.625rem", { lineHeight: "1.35" }],  /* 26px */
        "3xl": ["2rem", { lineHeight: "1.3" }],       /* 32px */
        "4xl": ["2.5rem", { lineHeight: "1.2" }],     /* 40px */
        "5xl": ["3.25rem", { lineHeight: "1.1" }],    /* 52px */
      },
      boxShadow: {
        "glow-sm": "0 0 12px hsl(var(--primary) / 0.12)",
        "glow": "0 0 20px hsl(var(--primary) / 0.18), 0 0 40px hsl(var(--primary) / 0.08)",
        "glow-lg": "0 0 32px hsl(var(--primary) / 0.25), 0 0 64px hsl(var(--primary) / 0.12)",
        "glow-emerald": "0 0 20px hsl(158 64% 52% / 0.18)",
        "glow-amber": "0 0 20px hsl(38 92% 50% / 0.18)",
        "glow-crimson": "0 0 20px hsl(0 72% 51% / 0.18)",
        "inset-border": "inset 0 1px 0 0 hsl(var(--border))",
      },
      backgroundImage: {
        "noise": "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E\")",
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "slide-left": {
          from: { opacity: "0", transform: "translateX(16px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "pulse-dot": {
          "0%, 100%": { opacity: "1", transform: "scale(1)" },
          "50%": { opacity: "0.5", transform: "scale(0.85)" },
        },
        "graph-fade": {
          from: { opacity: "0", transform: "scale(0.85)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "fade-in": "fade-in 0.3s ease-out",
        "slide-up": "slide-up 0.3s ease-out",
        "slide-left": "slide-left 0.3s ease-out",
        shimmer: "shimmer 1.8s ease-in-out infinite",
        "pulse-dot": "pulse-dot 1.8s ease-in-out infinite",
        "graph-fade": "graph-fade 0.4s ease-out forwards",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
