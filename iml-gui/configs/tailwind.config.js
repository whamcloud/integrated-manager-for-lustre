// [...range(1,5,2)] => [1,3,5]
function* range(start, end, step) {
  if (start > end) return;
  yield start;
  yield* range(start + step, end, step);
}

// For NodeJS < 12
Object.fromEntries =
  Object.fromEntries ||
  ((iterable) => {
    return [...iterable].reduce((obj, [key, val]) => {
      obj[key] = val;
      return obj;
    }, {});
  });

module.exports = {
  future: {
    purgeLayersByDefault: true,
    removeDeprecatedGapUtilities: true,
  },
  theme: {
    screens: {
      sm: "569px",
      // => @media (min-width: 569px) { ... }

      md: "769px",
      // => @media (min-width: 769px) { ... }

      lg: "1025px",
      // => @media (min-width: 1025px) { ... }

      xl: "1701px",
      // => @media (min-width: 1701px) { ... }
    },
    fontFamily: {
      display: ["Inter", "sans-serif"],
      body: ["Inter", "sans-serif"],
      monospace: ["Courier New", "monospace"],
      ordinary: ["Arial", "sans-serif"],
      sans: [
        "-apple-system",
        "BlinkMacSystemFont",
        "Segoe UI",
        "Roboto",
        "Helvetica Neue",
        "Arial",
        "Noto Sans",
        "sans-serif",
        "Apple Color Emoji",
        "Segoe UI Emoji",
        "Segoe UI Symbol",
        "Noto Color Emoji",
      ],
    },
    fontSize: (() => {
      const x = Object.fromEntries(
        [
          ...range(15, 35, 1),
          ...range(40, 60, 5),
          ...range(70, 120, 10),
        ].map((i) => [i, `${i}px`])
      );

      return {
        ...x,
        xs: "0.75rem",
        sm: "0.875rem",
        base: "1rem",
        lg: "1.125rem",
        xl: "1.25rem",
        "2xl": "1.5rem",
        "3xl": "1.875rem",
        "4xl": "2.25rem",
        "5xl": "3rem",
        "6xl": "4rem",
      };
    })(),
    opacity: (() => {
      return Object.fromEntries(
        [...range(0, 100, 10)].map((i) => [i, i / 100])
      );
    })(),
    extend: {
      boxShadow: {
        "2xl-above":
          "0 25px 50px 15px rgba(0, 0, 0, 0.25), 0 10px 10px 10px rgba(0, 0, 0, 0.25)",
        glow: "0 0 5px 2px hsl(205, 97%, 85%)",
      },
      margin: {
        "-10vh": "-10vh",
        "10vw": "10vw",
        "-30": "-7.5rem",
        "-80": "-20rem",
        "-92": "-23rem",
        "-120": "-30rem",
        "-260px": "-260px",
        "-545px": "-545px",
        "-670px": "-670px",
        "-820px": "-820px",
        "-1230px": "-1230px",
        38: "9.5rem",
        72: "18rem",
        96: "24rem",
        108: "27rem",
        132: "33rem",
        "310px": "310px",
        "790px": "790px",
        "1290px": "1290px",
        "1310px": "1310px",
        "1760px": "1760px",
        "2340px": "2340px",
        "2840px": "2840px",
        "3040px": "3040px",
        "3870px": "3870px",
        "5030px": "5030px",
        "6070px": "6070px",
      },
      padding: {
        84: "21rem",
        96: "24rem",
      },
      inset: {
        "1/2": "50%",
        full: "100%",
        "-full": "-100%",
        "-50vw": "-50vw",
      },
      width: {
        36: "9rem",
        76: "19rem",
        xs: "20rem",
        96: "24rem",
        100: "25rem",
        md: "28rem",
        120: "30rem",
        132: "33rem",
        204: "51rem",
        216: "54rem",
        236: "59rem",
        "70px": "70px",
        "265px": "265px",
        "385px": "385px",
        "520px": "520px",
        "570px": "570px",
        "750px": "750px",
        "860px": "860px",
        "900px": "900px",
        "1090px": "1090px",
        "1240px": "1240px",
        "1300px": "1300px",
        "1640px": "1640px",
        "2460px": "2460px",
        "2560px": "2560px",
        "50vh": "50vh",
        "50vw": "50vw",
      },
      maxWidth: {
        none: "none",
        "8xl": "88rem",
        400: "100rem",
      },
      minWidth: {
        6: "1.5rem",
      },
      height: {
        "main-content": "calc(100vh - 6.6rem)",
        18: "4.5rem",
        72: "18rem",
        "3px": "3px",
        "300px": "300px",
        "320px": "320px",
        "360px": "360px",
        "420px": "420px",
        "550px": "550px",
        "570px": "570px",
        "580px": "580px",
        "600px": "600px",
        "690px": "690px",
        "790px": "790px",
        "860px": "860px",
        "890px": "890px",
        "930px": "930px",
        "980px": "980px",
        "1090px": "1090px",
        "1160px": "1160px",
        "1240px": "1240px",
        "1300px": "1300px",
        "1340px": "1340px",
        "1420px": "1420px",
        "1580px": "1580px",
        "2330px": "2330px",
        "2360px": "2360px",
        "2560px": "2560px",
        "3670px": "3670px",
        80: "20rem",
        96: "24rem",
      },
      minHeight: {
        80: "20rem",
      },
      borderRadius: {
        "28px": "28px",
        "45px": "45px",
        "55px": "55px",
        "90px": "90px",
        "110px": "110px",
        "140px": "140px",
        "260px": "260px",
        "330px": "330px",
      },
      borderWidth: {
        3: "3px",
      },
      textColor: {
        active: "#3793FF",
      },
      cursor: {
        "ew-resize": "ew-resize",
      },
      colors: {
        black: "#000",
        white: "#FFF",
        menu: "#344151",
        "menu-active": "#1C2A3C",
        "blue-1000": "#0D1B2C",
        "throughput-background": "#5350FB",
      },
      strokeWidth: {
        3: "3",
        4: "4",
        5: "5",
        6: "6",
        8: "8",
        10: "10",
        20: "20",
      },
      transitionProperty: {
        stroke_dashoffset: "stroke-dashoffset",
      },
    },
  },
  variants: {
    backgroundColor: ({ after }) => after(["form-invalid", "disabled"]),
    borderColor: ({ after }) => after(["checked"]),
    borderWidth: ["responsive", "last", "hover", "focus"],
    cursor: ({ after }) => after(["form-invalid", "disabled"]),
    display: ["group-hover", "group-focus", "responsive"],
    pointerEvents: ({ after }) => after(["form-invalid"]),
    textColor: ["hover", "group-hover", "focus", "checked"],
  },
  plugins: [
    function ({ addVariant }) {
      addVariant("group-focus", ({ container }) => {
        container.walkRules((rule) => {
          rule.selector = `.group:focus-within .group-focus\\:${rule.selector.slice(
            1
          )}`;
        });
      });
    },
    function ({ addVariant }) {
      addVariant("form-invalid", ({ container }) => {
        container.walkRules((rule) => {
          rule.selector = `form:invalid .form-invalid\\:${rule.selector.slice(
            1
          )}`;
        });
      });
    },
    function ({ addVariant, e }) {
      addVariant("invalid", ({ modifySelectors, separator }) => {
        modifySelectors(
          ({ className }) => `.${e(`invalid${separator}${className}`)}:invalid`
        );
      });
    },
  ],
};
