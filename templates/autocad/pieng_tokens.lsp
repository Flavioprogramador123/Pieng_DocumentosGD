;;; pieng_tokens.lsp — PIENG Soluções Energéticas
;;; Fallback: lê tokens_autocad.txt e substitui {{TOKEN}} em TEXT/MTEXT.
;;; Fluxo normal: usar planta.dxf gerado pela web (já preenchido).

(vl-load-com)

(defun pieng-read-tokens (filepath / f line pos key val alist)
  (setq alist '())
  (setq f (open filepath "r"))
  (if (not f)
    alist
    (progn
      (while (setq line (read-line f))
        (if (and (> (strlen line) 0) (/= (substr line 1 1) "#"))
          (if (setq pos (vl-string-search "=" line))
            (progn
              (setq key (strcase (vl-string-trim " {}" (substr line 1 pos))))
              (setq val (substr line (+ pos 2)))
              (setq alist (cons (cons key val) alist))
            )
          )
        )
      )
      (close f)
      (reverse alist)
    )
  )
)

(defun pieng-replace-str (src pairs / out item tok repl)
  (setq out src)
  (foreach item pairs
    (setq tok (car item))
    (setq repl (cdr item))
    (while (vl-string-search tok out)
      (setq out (vl-string-subst repl tok out))
    )
    ;; MTEXT escapado: \{\{TOKEN\}\}
    (setq tok (strcat "\\{\\{" (vl-string-trim "{}" tok) "\\}\\}"))
    (while (vl-string-search tok out)
      (setq out (vl-string-subst repl tok out))
    )
  )
  out
)

(defun pieng-pairs-for-replace (alist / pairs item k v)
  (setq pairs '())
  (foreach item alist
    (setq k (car item))
    (setq v (cdr item))
    (if (and k v (/= v ""))
      (setq pairs (cons (cons (strcat "{{" k "}}") v) pairs))
    )
  )
  (reverse pairs)
)

(defun pieng-update-text-entity (ent pairs / ed typ txt newtxt)
  (setq ed (entget ent))
  (setq typ (cdr (assoc 0 ed)))
  (if (member typ '("TEXT" "MTEXT"))
    (progn
      (setq txt (cdr (assoc 1 ed)))
      (setq newtxt (pieng-replace-str txt pairs))
      (if (/= newtxt txt)
        (entmod (subst (cons 1 newtxt) (assoc 1 ed) ed))
      )
    )
  )
)

(defun pieng-walk-all-texts (pairs / ss i ent)
  (setq ss (ssget "_X" '((0 . "TEXT,MTEXT"))))
  (if ss
    (progn
      (setq i 0)
      (repeat (sslength ss)
        (pieng-update-text-entity (ssname ss i) pairs)
        (setq i (1+ i))
      )
    )
  )
)

(defun c:PIENG_TOKENS (/ fp alist pairs)
  (setq fp (getfiled "tokens_autocad.txt" "" "txt" 16))
  (if fp
    (progn
      (setq alist (pieng-read-tokens fp))
      (setq pairs (pieng-pairs-for-replace alist))
      (pieng-walk-all-texts pairs)
      (princ (strcat "\n[PIENG] Tokens aplicados: " (itoa (length pairs))))
    )
    (princ "\n[PIENG] Cancelado.")
  )
  (princ)
)

(princ "\nPIENG: comando PIENG_TOKENS carregado.")
(princ)
