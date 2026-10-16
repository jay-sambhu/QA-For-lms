import React from "react";
import Link from "next/link";
import { TbArrowRight, TbHome, TbArticle } from "react-icons/tb";
import { Surface3D } from "../components/three";
import c from "./content3d.module.css";

export default function NotFound() {
  return (
    <div className="page-shell">
      <Surface3D as="section" ring pad="lg" className={`${c.nf} enter-3d`} aria-labelledby="nf-title">
        <div className={c.nfCopy}>
          <span className="chip chip--danger chip--dot">404 · Not mapped</span>
          <span className={`stat-number ${c.nfCode}`} aria-hidden="true">404</span>
          <h1 id="nf-title" className={c.nfTitle}>
            Our crawler could not find this page
          </h1>
          <p className={c.nfDesc}>
            The link may be broken, the page may have moved, or it was never published. Everything else on the map is
            still where you left it.
          </p>
          <div className={c.nfActions}>
            <Link href="/" className="btn btn-primary">
              <TbHome size={18} /> Back to home <TbArrowRight size={18} />
            </Link>
            <Link href="/blog" className="btn btn-secondary">
              <TbArticle size={18} /> Read the blog
            </Link>
          </div>
        </div>

        <div className={c.nfScene} aria-hidden="true">
          <span className={c.nfFloor} />
          <span className={c.nfLink} />
          <span className={`${c.nfNode} ${c.nfNodeA}`}><i /><i /><i /></span>
          <span className={`${c.nfNode} ${c.nfNodeB}`}><i /><i /><i /></span>
          <span className={`${c.nfNode} ${c.nfNodeC}`}><i /><i /><i /></span>
          <span className={c.nfMissing}>?</span>
          <span className={c.nfPin}><i className={c.nfPinPulse} /></span>
        </div>
      </Surface3D>
    </div>
  );
}
