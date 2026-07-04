/**
 * CreatableAutocomplete — searchable dropdown that allows free-text creation.
 *
 * Pattern: text input + portal-rendered dropdown of suggestions.
 * User can pick an existing value OR type a new one. Not a closed select.
 *
 * The dropdown renders via React Portal (attached to document.body) so it
 * is never clipped by parent overflow:hidden / overflow:auto containers
 * like table wrappers. Positioned dynamically based on input coordinates.
 *
 * Uses portal <div> (NOT Popover) because Radix Popover's
 * onPointerDown preventDefault blocks input focus on iOS touch devices.
 *
 * Props:
 *   value        — current field value (string)
 *   onChange      — (newValue: string) => void
 *   options       — string[] of suggestions (loaded from API)
 *   placeholder   — input placeholder text
 *   className     — additional CSS classes for the input
 *   maxSuggestions — max items to show (default 6)
 *   disabled      — disable the input
 */
import React, { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { Input } from './ui/input';

export const CreatableAutocomplete = ({
  value,
  onChange,
  options = [],
  placeholder = '',
  className = '',
  maxSuggestions = 6,
  disabled = false,
}) => {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0, width: 0 });
  const inputRef = useRef(null);
  const dropdownRef = useRef(null);

  // Recalculate position when dropdown opens
  const updatePosition = useCallback(() => {
    if (inputRef.current) {
      const rect = inputRef.current.getBoundingClientRect();
      setPos({
        top: rect.bottom + window.scrollY + 4,
        left: rect.left + window.scrollX,
        width: rect.width,
      });
    }
  }, []);

  // Close dropdown on outside click/touch
  useEffect(() => {
    const handleOutside = (e) => {
      if (
        inputRef.current && !inputRef.current.contains(e.target) &&
        dropdownRef.current && !dropdownRef.current.contains(e.target)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleOutside);
    document.addEventListener('touchstart', handleOutside);
    return () => {
      document.removeEventListener('mousedown', handleOutside);
      document.removeEventListener('touchstart', handleOutside);
    };
  }, []);

  // Filter options: case-insensitive match, exclude exact match
  const filtered = useMemo(() => {
    if (!value) return options.slice(0, maxSuggestions);
    const q = value.toLowerCase().trim();
    return options
      .filter(opt => opt.toLowerCase().includes(q) && opt.toLowerCase() !== q)
      .slice(0, maxSuggestions);
  }, [value, options, maxSuggestions]);

  const showDropdown = open && filtered.length > 0;

  // Update position on open and on scroll/resize
  useEffect(() => {
    if (showDropdown) {
      updatePosition();
      window.addEventListener('scroll', updatePosition, true);
      window.addEventListener('resize', updatePosition);
      return () => {
        window.removeEventListener('scroll', updatePosition, true);
        window.removeEventListener('resize', updatePosition);
      };
    }
  }, [showDropdown, updatePosition]);

  return (
    <>
      <Input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          setOpen(true);
        }}
        onFocus={() => {
          updatePosition();
          setOpen(true);
        }}
        onBlur={() => {
          setTimeout(() => setOpen(false), 150);
        }}
        placeholder={placeholder}
        className={className}
        disabled={disabled}
      />
      {showDropdown && createPortal(
        <div
          ref={dropdownRef}
          className="fixed z-[9999] bg-popover border rounded-lg shadow-lg p-1 max-h-40 overflow-y-auto"
          style={{
            top: pos.top,
            left: pos.left,
            width: pos.width,
            position: 'absolute',
          }}
        >
          {filtered.map((opt) => (
            <button
              key={opt}
              type="button"
              className="w-full text-left px-2 py-1.5 text-sm rounded hover:bg-muted active:bg-muted truncate"
              onMouseDown={(e) => {
                e.preventDefault();
                onChange(opt);
                setOpen(false);
              }}
            >
              {opt}
            </button>
          ))}
        </div>,
        document.body
      )}
    </>
  );
};

export default CreatableAutocomplete;
