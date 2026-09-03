import { SectionHeading } from "@/components/section-heading"
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"
import { TELEGRAM_BOT_HANDLE } from "@/lib/utils"

const FAQS = [
  {
    question: "Do I need to install anything?",
    answer:
      `No. If you already have Telegram, you simply open a chat with ${TELEGRAM_BOT_HANDLE} and forward the message to it, the same way you would forward it to a friend. There is no app to download, no account to create and nothing to pay.`,
  },
  {
    question: "How long does a check take?",
    answer:
      "Usually about 30 seconds. Claims that have already been checked for someone else come back almost immediately, because the answer is served from the verified-claims cache instead of being worked out again.",
  },
  {
    question: "What if TrustLens does not know the answer?",
    answer:
      "It tells you. When no approved source covers the claim, the reply is Unverified rather than a guess. That is deliberate: a confident-sounding wrong answer would be worse than no answer at all.",
  },
  {
    question: "Can I trust the verdict?",
    answer:
      "Check it yourself, and we make that easy. Every verdict lists the sources it relied on, so you can open them and read the original. The confidence level tells you how strongly the evidence supported the conclusion. Where the system is uncertain, a human fact-checker reviews the case.",
  },
  {
    question: "What happens to the message I forward?",
    answer:
      "It is used to run the check and then discarded. Content is kept only if you explicitly choose to contribute it to the community review layer. Processing and storage stay on Singapore-region infrastructure, in line with the Personal Data Protection Act.",
  },
  {
    question: "Is this a government service?",
    answer:
      "No. TrustLens SG is an independent student-led project from Singapore Management University. It is designed to work alongside national fact-checking and reporting channels, and it points you to official sources rather than standing in for them.",
  },
  {
    question: "Can I use it on WhatsApp?",
    answer:
      "Not yet. Telegram is live today. WhatsApp is planned for a later phase, using the WhatsApp Business API, so that the same check works in whichever app the message arrived in.",
  },
  {
    question: "Does it work with photos, videos and voice notes?",
    answer:
      "Text messages and forwarded links work today. Image, video and voice checking, including deepfake and voice-clone detection, is in development and is the next major addition.",
  },
]

export function Faq() {
  return (
    <section id="faq" className="border-b border-border bg-background py-16 lg:py-24">
      <div className="container">
        <SectionHeading
          eyebrow="Common questions"
          title="Questions people ask before their first check"
        />

        <div className="mt-10 max-w-3xl">
          <Accordion type="single" collapsible className="w-full border-t border-border">
            {FAQS.map((faq, index) => (
              <AccordionItem key={faq.question} value={`item-${index}`}>
                <AccordionTrigger>{faq.question}</AccordionTrigger>
                <AccordionContent>
                  <p className="text-base leading-relaxed">{faq.answer}</p>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </div>
    </section>
  )
}
