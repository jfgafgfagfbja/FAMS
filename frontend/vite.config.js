import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'

export default defineConfig({
  plugins: [
    react(),
    // Chi sinh report khi ANALYZE=1 (vd `ANALYZE=1 npm run build`) - khong anh
    // huong build binh thuong.
    process.env.ANALYZE && visualizer({
      filename: 'dist/stats.html',
      gzipSize: true,
      brotliSize: true,
      template: 'treemap',
    }),
  ],
  server: { port: 5173 },
  build: {
    rollupOptions: {
      output: {
        // Gop cac trang lazy-load cung nhom vao 1 chunk ten rieng (thay vi de
        // Rollup tao 1 chunk nho cho tung trang) - SV chi tai duoc 'attendance'
        // qua route /attendance/:id, khong bao gio phai tai 'admin' (chua
        // recharts, nang nhat trong bundle) hay nguoc lai.
        manualChunks(id) {
          const nmIndex = id.indexOf('node_modules')
          if (nmIndex !== -1) {
            // Xac dinh chinh xac ten package npm (khong dung regex doi voi
            // duong dan day du - tranh khop nham vd "react" ben trong
            // "@phosphor-icons/react") de gan chunk chinh xac tuyet doi.
            const rest = id.slice(nmIndex + 'node_modules/'.length).replace(/\\/g, '/')
            const segs = rest.split('/')
            const pkg = segs[0].startsWith('@') ? `${segs[0]}/${segs[1]}` : segs[0]

            // Toan bo chuoi dependency rieng cua recharts (khong package nao o
            // day duoc dung boi code nao khac ngoai Dashboard.jsx) - gop chung
            // vao chunk 'admin' de khong lam nang chunk vendor tai chung.
            const rechartsChain = new Set([
              'recharts', 'victory-vendor', '@reduxjs/toolkit', 'redux', 'react-redux',
              'reselect', 'immer', 'decimal.js-light', 'es-toolkit', 'eventemitter3',
              'tiny-invariant', 'use-sync-external-store', 'clsx',
            ])
            if (rechartsChain.has(pkg)) return 'admin'

            // react-webcam chi duoc AttendanceScreen va EnrollFace dung - tach
            // rieng de khong lam nang chunk vendor dung chung cho moi trang.
            if (pkg === 'react-webcam') return 'vendor-webcam'

            if (['react', 'react-dom', 'scheduler', 'react-router', 'react-router-dom', '@remix-run/router'].includes(pkg)) {
              return 'vendor-react'
            }
            return 'vendor'
          }

          // api.js/theme.js duoc App.jsx import TINH (khong qua lazy) va cung
          // duoc moi trang admin dung - neu khong ghim vao 'vendor', Rollup tu
          // gop chung vao chunk 'admin' (vi la dep dung chung giua cac trang
          // admin), tao lien ket tinh entry -> admin khien 'admin' bi preload
          // cho MOI nguoi dung (kiem chung qua index.html sinh ra).
          if (/[\\/]src[\\/](api|theme)\.js$/.test(id)) {
            return 'vendor'
          }

          if (/[\\/]src[\\/]pages[\\/](Dashboard|Students|Lecturers|Classes|ClassDetail|AdminSchedules|FaceReview)\.jsx$/.test(id)) {
            return 'admin'
          }
          if (/[\\/]src[\\/]pages[\\/](AttendanceScreen|SessionRecords|SessionsList|LecturerReports)\.jsx$/.test(id)) {
            return 'attendance'
          }
          if (/[\\/]src[\\/]pages[\\/]EnrollFace\.jsx$/.test(id)) {
            return 'enroll'
          }
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/setupTests.js',
    globals: true,
    // e2e/ la test Playwright (chay qua `npm run test:e2e`), khong phai vitest -
    // loai tru de vitest khong co gang chay nham voi test()/expect() cua Playwright.
    exclude: ['e2e/**', 'node_modules/**'],
  },
})
