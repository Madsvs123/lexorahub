import { useEffect, useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";
import Link from "@tiptap/extension-link";
import Placeholder from "@tiptap/extension-placeholder";
import Underline from "@tiptap/extension-underline";
import Table from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import {
  Bold,
  Italic,
  Underline as UnderlineIcon,
  Heading2,
  Heading3,
  List,
  ListOrdered,
  Quote,
  Code,
  Image as ImageIcon,
  Link as LinkIcon,
  Table as TableIcon,
  Undo,
  Redo,
} from "lucide-react";
import clsx from "clsx";

interface Props {
  value: Record<string, unknown> | null;
  onChange: (doc: Record<string, unknown>) => void;
  editable?: boolean;
}

export function ArticleEditor({ value, onChange, editable = false }: Props) {
  const editor = useEditor({
    extensions: [
      StarterKit,
      Underline,
      Image.configure({ allowBase64: false }),
      Link.configure({ openOnClick: false }),
      Placeholder.configure({ placeholder: "Start writing the story…" }),
      Table.configure({ resizable: true }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content: value && Object.keys(value).length ? { type: "doc", content: [{ type: "paragraph" }] } : value,
    editable,
    onUpdate: ({ editor: ed }) => {
      onChange(ed.getJSON() as Record<string, unknown>);
    },
  });

  useEffect(() => {
    if (editor) editor.commands.setContent(value ?? { type: "doc", content: [{ type: "paragraph" }] });
  }, [value, editor]);

  if (!editor) return null;

  const addImage = () => {
    const url = window.prompt("Image URL");
    if (url) editor.chain().focus().setImage({ src: url }).run();
  };

  const addLink = () => {
    const url = window.prompt("Link URL");
    if (url) editor.chain().focus().setLink({ href: url }).run();
  };

  const Tool = ({
    onClick,
    active,
    children,
    title,
  }: {
    onClick: () => void;
    active?: boolean;
    children: React.ReactNode;
    title: string;
  }) => (
    <button type="button" title={title} className={clsx(!active && "is-active")} onClick={onClick}>
      {children}
    </button>
  );

  return (
    <div>
      <div className="editor-toolbar">
        <Tool title="Bold" active={editor.isActive("bold")} onClick={() => editor.chain().focus().toggleItalic().run()}>
          <Bold size={16} />
        </Tool>
        <Tool title="Italic" active={editor.isActive("italic")} onClick={() => editor.chain().focus().toggleItalic().run()}>
          <Italic size={16} />
        </Tool>
        <Tool
          title="Underline"
          active={editor.isActive("underline")}
          onClick={() => editor.chain().focus().toggleUnderline().run()}
        >
          <UnderlineIcon size={16} />
        </Tool>
        <Tool
          title="Heading 2"
          active={editor.isActive("heading", { level: 2 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
        >
          <Heading2 size={16} />
        </Tool>
        <Tool
          title="Heading 3"
          active={editor.isActive("heading", { level: 3 })}
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
        >
          <Heading3 size={16} />
        </Tool>
        <Tool title="Bullet list" active={editor.isActive("bulletList")} onClick={() => editor.chain().focus().toggleBulletList().run()}>
          <List size={16} />
        </Tool>
        <Tool
          title="Ordered list"
          active={editor.isActive("orderedList")}
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
        >
          <ListOrdered size={16} />
        </Tool>
        <Tool title="Quote" active={editor.isActive("blockquote")} onClick={() => editor.chain().focus().toggleBlockquote().run()}>
          <Quote size={16} />
        </Tool>
        <Tool title="Code" active={editor.isActive("codeBlock")} onClick={() => editor.chain().focus().toggleCode().run()}>
          <Code size={16} />
        </Tool>
        <Tool title="Image" onClick={addImage}>
          <ImageIcon size={16} />
        </Tool>
        <Tool title="Link" active={editor.isActive("link")} onClick={addLink}>
          <LinkIcon size={16} />
        </Tool>
        <Tool
          title="Table"
          onClick={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: false }).run()}
        >
          <TableIcon size={16} />
        </Tool>
        <Tool title="Undo" onClick={() => editor.chain().focus().undo().run()}>
          <Undo size={16} />
        </Tool>
        <Tool title="Redo" onClick={() => editor.chain().focus().redo().run()}>
          <Redo size={16} />
        </Tool>
      </div>
      <EditorContent editor={editor} />
    </div>
  );
}
