import * as React from "react"
import { useIsMobile } from "../../hooks/useIsMobile"

import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "./dialog"

import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "./drawer"

/**
 * ResponsiveDialog — renders a centered Dialog on desktop,
 * a bottom-sheet Drawer on mobile.
 *
 * Usage is identical to Dialog:
 *
 *   <ResponsiveDialog open={open} onOpenChange={setOpen}>
 *     <ResponsiveDialogTrigger asChild>
 *       <Button>Open</Button>
 *     </ResponsiveDialogTrigger>
 *     <ResponsiveDialogContent>
 *       <ResponsiveDialogHeader>
 *         <ResponsiveDialogTitle>Title</ResponsiveDialogTitle>
 *         <ResponsiveDialogDescription>Description</ResponsiveDialogDescription>
 *       </ResponsiveDialogHeader>
 *       {children}
 *       <ResponsiveDialogFooter>
 *         <Button>Action</Button>
 *       </ResponsiveDialogFooter>
 *     </ResponsiveDialogContent>
 *   </ResponsiveDialog>
 */

const ResponsiveDialog = ({ children, ...props }) => {
  const isMobile = useIsMobile()
  const Comp = isMobile ? Drawer : Dialog
  return <Comp {...props}>{children}</Comp>
}

const ResponsiveDialogTrigger = ({ children, ...props }) => {
  const isMobile = useIsMobile()
  const Comp = isMobile ? DrawerTrigger : DialogTrigger
  return <Comp {...props}>{children}</Comp>
}

const ResponsiveDialogContent = ({ children, className, ...props }) => {
  const isMobile = useIsMobile()
  if (isMobile) {
    return (
      <DrawerContent className={className} {...props}>
        <div className="max-h-[85vh] overflow-y-auto px-4 pb-4">
          {children}
        </div>
      </DrawerContent>
    )
  }
  return (
    <DialogContent className={className} {...props}>
      {children}
    </DialogContent>
  )
}

const ResponsiveDialogHeader = ({ children, ...props }) => {
  const isMobile = useIsMobile()
  const Comp = isMobile ? DrawerHeader : DialogHeader
  return <Comp {...props}>{children}</Comp>
}

const ResponsiveDialogFooter = ({ children, ...props }) => {
  const isMobile = useIsMobile()
  const Comp = isMobile ? DrawerFooter : DialogFooter
  return <Comp {...props}>{children}</Comp>
}

const ResponsiveDialogTitle = ({ children, ...props }) => {
  const isMobile = useIsMobile()
  const Comp = isMobile ? DrawerTitle : DialogTitle
  return <Comp {...props}>{children}</Comp>
}

const ResponsiveDialogDescription = ({ children, ...props }) => {
  const isMobile = useIsMobile()
  const Comp = isMobile ? DrawerDescription : DialogDescription
  return <Comp {...props}>{children}</Comp>
}

const ResponsiveDialogClose = ({ children, ...props }) => {
  const isMobile = useIsMobile()
  const Comp = isMobile ? DrawerClose : DialogClose
  return <Comp {...props}>{children}</Comp>
}

export {
  ResponsiveDialog,
  ResponsiveDialogTrigger,
  ResponsiveDialogContent,
  ResponsiveDialogHeader,
  ResponsiveDialogFooter,
  ResponsiveDialogTitle,
  ResponsiveDialogDescription,
  ResponsiveDialogClose,
}
