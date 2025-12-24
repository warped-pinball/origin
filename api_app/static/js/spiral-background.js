(() => {
  function renderSpiralBackground({ animated = false } = {}) {
    if (document.body.dataset.spiralApplied === "true") {
      return;
    }

    const canvas = document.createElement("canvas");
    if (animated) {
      canvas.id = "spiral-bg";
      canvas.setAttribute("aria-hidden", "true");
      Object.assign(canvas.style, {
        position: "fixed",
        inset: "0",
        width: "100vw",
        height: "100vh",
        display: "block",
        pointerEvents: "none",
        zIndex: "0",
      });
      document.body.prepend(canvas);
    }

    const gl = canvas.getContext("webgl", { antialias: true });
    if (!gl) {
      console.warn("WebGL not supported; spiral background disabled.");
      return;
    }

    const vertexSource = `
      attribute vec2 a_position;
      void main() {
        gl_Position = vec4(a_position, 0.0, 1.0);
      }
    `;

    const fragmentSource = `
      precision mediump float;

      uniform vec2 u_resolution;
      uniform float u_time;
      uniform float u_pixelRadius; // radius where center color fully gives way to stripes

      void main() {
        float minSide = min(u_resolution.x, u_resolution.y);
        vec2 center = u_resolution * 0.5;
        vec2 p = (gl_FragCoord.xy - center) / minSide; // roughly [-0.5, 0.5]

        float freq = 0.075;                 // lower = slower
        float phase = u_time * freq;
        float twistTurns = 0.22 * sin(phase);

        float rotationScale = 0.6;          // overall rotation amplitude (radians)
        float rotationAngle = rotationScale * (-cos(phase));

        float s = sin(rotationAngle);
        float c = cos(rotationAngle);
        vec2 pr = vec2(
          c * p.x - s * p.y,
          s * p.x + c * p.y
        );

        float r = length(pr);
        float angle = atan(pr.y, pr.x);
        float angle01 = (angle + 3.14159265359) / (2.0 * 3.14159265359);

        float stripes = 12.0;

        float twistedAngle = angle01 + r * twistTurns;

        float raw = twistedAngle * stripes;
        float stripeIndex = floor(raw);
        float local = fract(raw);

        vec3 colorA = vec3(146.0 / 255.0, 199.0 / 255.0, 215.0 / 255.0);
        vec3 colorB = vec3(202.0 / 255.0, 245.0 / 255.0, 254.0 / 255.0);

        float parity = mod(stripeIndex, 2.0);
        vec3 stripeColorA = (parity < 0.5) ? colorA : colorB;
        vec3 stripeColorB = (parity < 0.5) ? colorB : colorA;

        float edgeWidthLocal = 0.01;
        float mask = smoothstep(0.5 - edgeWidthLocal, 0.5 + edgeWidthLocal, local);

        vec3 stripeColor = mix(stripeColorA, stripeColorB, mask);

        vec3 centerColor = colorB;
        float centerBlend = smoothstep(0.0, u_pixelRadius, r);
        vec3 finalColor = mix(centerColor, stripeColor, centerBlend);

        gl_FragColor = vec4(finalColor, 1.0);
      }
    `;

    function createShader(type, source) {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        console.error(gl.getShaderInfoLog(shader));
        gl.deleteShader(shader);
        return null;
      }
      return shader;
    }

    function createProgram(vsSource, fsSource) {
      const vs = createShader(gl.VERTEX_SHADER, vsSource);
      const fs = createShader(gl.FRAGMENT_SHADER, fsSource);
      if (!vs || !fs) return null;
      const program = gl.createProgram();
      gl.attachShader(program, vs);
      gl.attachShader(program, fs);
      gl.linkProgram(program);
      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        console.error(gl.getProgramInfoLog(program));
        gl.deleteProgram(program);
        return null;
      }
      return program;
    }

    const program = createProgram(vertexSource, fragmentSource);
    if (!program) {
      return;
    }
    gl.useProgram(program);

    const positionBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, positionBuffer);
    const positions = new Float32Array([
      -1, -1,
       1, -1,
      -1,  1,
      -1,  1,
       1, -1,
       1,  1
    ]);
    gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);

    const aPosition = gl.getAttribLocation(program, "a_position");
    gl.enableVertexAttribArray(aPosition);
    gl.vertexAttribPointer(aPosition, 2, gl.FLOAT, false, 0, 0);

    const uResolution = gl.getUniformLocation(program, "u_resolution");
    const uTime = gl.getUniformLocation(program, "u_time");
    const uPixelRadius = gl.getUniformLocation(program, "u_pixelRadius");

    const STATIC_TIME_SECONDS = 21; // provides a nicely curved spiral for static pages
    const MAX_DEVICE_PIXEL_RATIO = 1.75;
    const startTime = performance.now();

    let lastDisplayWidth = 0;
    let lastDisplayHeight = 0;
    let firstFrameRendered = false;
    let needsResize = true;

    function resizeCanvas(displayWidth, displayHeight) {
      const resized = canvas.width !== displayWidth || canvas.height !== displayHeight;
      if (resized) {
        canvas.width = displayWidth;
        canvas.height = displayHeight;
        gl.viewport(0, 0, canvas.width, canvas.height);
      }
      return resized;
    }

    function renderFrame(time) {
      const dpr = Math.min(window.devicePixelRatio || 1, MAX_DEVICE_PIXEL_RATIO);
      const displayWidth = Math.floor(window.innerWidth * dpr);
      const displayHeight = Math.floor(window.innerHeight * dpr);
      const dimensionsChanged =
        displayWidth !== lastDisplayWidth || displayHeight !== lastDisplayHeight;

      if (dimensionsChanged || needsResize || !firstFrameRendered) {
        const resized = resizeCanvas(displayWidth, displayHeight);
        if (resized || !firstFrameRendered) {
          lastDisplayWidth = displayWidth;
          lastDisplayHeight = displayHeight;
          const minSide = Math.min(canvas.width, canvas.height);
          const pixelRadius = 1.5 / minSide;

          gl.useProgram(program);
          gl.uniform2f(uResolution, canvas.width, canvas.height);
          gl.uniform1f(uPixelRadius, pixelRadius);
        }
        needsResize = false;
      }

      const elapsed = animated ? (time - startTime) * 0.001 : STATIC_TIME_SECONDS;

      gl.useProgram(program);
      gl.uniform1f(uTime, elapsed);

      gl.clearColor(0.0, 0.0, 0.0, 1.0);
      gl.clear(gl.COLOR_BUFFER_BIT);

      gl.drawArrays(gl.TRIANGLES, 0, 6);
      firstFrameRendered = true;
    }

    function applyStaticBackground() {
      renderFrame(performance.now());
      const dataUrl = canvas.toDataURL("image/png");
      const target = document.body;

      Object.assign(target.style, {
        backgroundImage: `url(${dataUrl})`,
        backgroundSize: "cover",
        backgroundRepeat: "no-repeat",
        backgroundPosition: "center",
        backgroundAttachment: "fixed",
        backgroundColor: "#202124",
      });

      document.body.dataset.spiralApplied = "true";
    }

    function startAnimatedRender() {
      function loop(time) {
        renderFrame(time);
        requestAnimationFrame(loop);
      }
      requestAnimationFrame(loop);
      window.addEventListener("resize", () => {
        needsResize = true;
      });
    }

    if (animated) {
      startAnimatedRender();
    } else {
      const debouncedStatic = () => {
        document.body.dataset.spiralApplied = "false";
        applyStaticBackground();
      };

      applyStaticBackground();
      window.addEventListener("resize", () => {
        clearTimeout(window.__spiralResizeTimeout);
        window.__spiralResizeTimeout = setTimeout(debouncedStatic, 150);
      });
    }
  }

  function init() {
    const mode = document.body.dataset.spiral || "static";
    renderSpiralBackground({ animated: mode === "animated" });
  }

  window.renderSpiralBackground = renderSpiralBackground;
  document.addEventListener("DOMContentLoaded", init);
})();
