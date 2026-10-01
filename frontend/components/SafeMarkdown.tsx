import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

// Model/report text rendered as Markdown only. No raw-HTML plugin: HTML in the
// source stays inert text, and react-markdown drops javascript: URLs.
// Images are dropped (a remote image would leak the viewer's IP); links must be https.
export default function SafeMarkdown({ content, light = false }: { content: string; light?: boolean }) {
  const text = light ? 'text-gray-700' : 'text-gray-300'
  const heading = light ? 'text-gray-900' : 'text-white'
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      disallowedElements={['img']}
      components={{
        h1: ({ children }) => <h1 className={`font-bold mt-6 mb-4 text-2xl ${heading}`}>{children}</h1>,
        h2: ({ children }) => <h2 className={`font-bold mt-6 mb-3 text-xl ${heading}`}>{children}</h2>,
        h3: ({ children }) => <h3 className={`font-semibold mt-4 mb-2 text-lg ${heading}`}>{children}</h3>,
        h4: ({ children }) => <h4 className={`font-semibold mt-3 mb-1 ${heading}`}>{children}</h4>,
        p: ({ children }) => <p className={`my-2 leading-relaxed ${text}`}>{children}</p>,
        strong: ({ children }) => <strong className={`font-semibold ${heading}`}>{children}</strong>,
        ul: ({ children }) => <ul className={`list-disc ml-5 my-2 space-y-1 ${text}`}>{children}</ul>,
        ol: ({ children }) => <ol className={`list-decimal ml-5 my-2 space-y-1 ${text}`}>{children}</ol>,
        hr: () => <hr className={light ? 'my-6 border-gray-200' : 'my-6 border-white/10'} />,
        a: ({ href, children }) =>
          href && href.startsWith('https://') ? (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-sparq-lime underline">{children}</a>
          ) : (
            <span>{children}</span>
          ),
        table: ({ children }) => <table className={`my-3 text-sm border-collapse ${text}`}>{children}</table>,
        th: ({ children }) => <th className="border border-white/10 px-2 py-1 text-left font-semibold">{children}</th>,
        td: ({ children }) => <td className="border border-white/10 px-2 py-1">{children}</td>,
      }}
    >
      {content}
    </ReactMarkdown>
  )
}
